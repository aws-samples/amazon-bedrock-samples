"""Helpers for the Advanced Prompt Optimization (APO) tutorial notebooks.

Single self-contained module — no cross-folder imports. Reusable parts
(`to_service_format`, `validate_service_template`, `write_jsonl`, `load_env`)
are ported verbatim from `apo-examples-handoff/common/template_utils.py`.

The public API is organized into five sections (in order):
  1. Env + boto3 clients
  2. Lambda lifecycle (deploy + smoke-test)
  3. Record builders (lambda / llmj / steering, with optional multimodal)
  4. S3, submit, poll, fetch (run_job is the one-shot orchestrator)
  5. Results parsing + Markdown renderers (IPython-friendly)
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from IPython.display import Markdown


HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE / "data"
TUTORIAL_S3_PREFIX = "apo-tutorial"
API_VERSION = "bedrock-2026-05-14"
N_SAMPLES_DEFAULT = 20


# ---------------------------------------------------------------------------
# 1. Env + boto3 clients
# ---------------------------------------------------------------------------

def load_env(path: Path = HERE / ".env") -> dict[str, str]:
    """Parse an `export K=V` .env file into a dict.

    Also exports each key to `os.environ` (bash-source semantics) **unless the
    variable is already set in the shell** — so a shell override always wins
    over the .env default. Required so toggles like `APO_USE_REFERENCE` flow
    transparently from setup.py → notebook.

    Exits with a friendly error if the file is missing.
    """
    if not path.exists():
        sys.exit(
            f"[error] {path} not found.\n"
            "        Run `python setup.py` first to bootstrap the environment."
        )
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        val = value.strip().strip('"').strip("'")
        env[key] = val
        os.environ.setdefault(key, val)
    return env


def make_clients(env: dict) -> tuple[Any, Any, Any]:
    """Return `(bedrock, s3, lambda_client)` boto3 clients."""
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    cfg = Config(retries={"max_attempts": 3, "mode": "standard"},
                 read_timeout=60, connect_timeout=10)
    bedrock = session.client("bedrock", config=cfg)
    s3 = session.client("s3")
    lambda_client = session.client("lambda")
    return bedrock, s3, lambda_client


# ---------------------------------------------------------------------------
# 2. Lambda lifecycle (for Lambda-metric notebooks only)
# ---------------------------------------------------------------------------

def _zip_lambda_source(source_py: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(source_py, arcname="lambda_function.py")
    return buf.getvalue()


def deploy_metric_lambda(example: str, env: dict, lambda_client=None) -> str:
    """Zip and create-or-update the metric Lambda for *example*.

    Names the function `apo-tutorial-<example>-metric`. Idempotent: if the
    function exists, only the code is updated (~3 s); otherwise it is created
    with the bundled execution role from `env["LAMBDA_ROLE_ARN"]`.

    Returns the function ARN.
    """
    if lambda_client is None:
        _, _, lambda_client = make_clients(env)
    function_name = f"apo-tutorial-{example}-metric"
    source = DATA_ROOT / example / "lambda_function.py"
    if not source.exists():
        raise FileNotFoundError(f"Lambda source not found: {source}")
    zip_bytes = _zip_lambda_source(source)

    try:
        lambda_client.get_function(FunctionName=function_name)
        lambda_client.update_function_code(FunctionName=function_name, ZipFile=zip_bytes)
        action = "updated"
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.10",
            Role=env["LAMBDA_ROLE_ARN"],
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30,
            MemorySize=512,
        )
        time.sleep(5)  # IAM propagation
        action = "created"

    arn = f"arn:aws:lambda:{env['REGION']}:{env['ACCOUNT_ID']}:function:{function_name}"
    print(f"[lambda] {action} {function_name}")
    return arn


def smoke_test_lambda(arn: str, env: dict, preds: list[str], golds: list[str],
                      lambda_client=None) -> dict:
    """Invoke the Lambda once with `{preds, golds}` and return the parsed response."""
    if lambda_client is None:
        _, _, lambda_client = make_clients(env)
    payload = json.dumps({"preds": preds, "golds": golds}).encode("utf-8")
    resp = lambda_client.invoke(FunctionName=arn, Payload=payload)
    body = json.loads(resp["Payload"].read())
    return body


# Identity pred/gold pair per lambda-mode example — used to verify each metric
# Lambda returns score=1.0 on a trivial perfect match before any APO job runs.
LAMBDA_SMOKE_INPUTS: dict[str, dict[str, list[str]]] = {
    "nestful": {
        "preds": ['[{"name":"add","arguments":{"arg_0":1,"arg_1":2},"label":"$var_1"}]'],
        "golds": ['[{"name":"add","arguments":{"arg_0":1,"arg_1":2},"label":"$var_1"}]'],
    },
    "mmvqa": {
        "preds": ["mitochondrial DNA"],
        "golds": ["mitochondrial DNA"],
    },
}


def lambda_arn_for(env: dict, example: str) -> str:
    """Return the deterministic ARN for an example's metric Lambda."""
    return (
        f"arn:aws:lambda:{env['REGION']}:{env['ACCOUNT_ID']}"
        f":function:apo-tutorial-{example}-metric"
    )


def setup_lambdas(env: dict, examples: list[str] | None = None,
                  lambda_client=None) -> dict[str, str]:
    """Deploy + smoke-test all lambda-mode metric Lambdas. Returns {example: arn}.

    Raises RuntimeError if any smoke test does not return score == 1.0.
    """
    if examples is None:
        examples = [e for e, m in EXAMPLES.items() if m["mode"] == "lambda"]
    if lambda_client is None:
        _, _, lambda_client = make_clients(env)
    arns: dict[str, str] = {}
    for ex in examples:
        arn = deploy_metric_lambda(ex, env, lambda_client=lambda_client)
        inputs = LAMBDA_SMOKE_INPUTS.get(ex)
        if inputs is None:
            print(f"[lambda] {ex}: no smoke-test inputs registered; skipping check")
            arns[ex] = arn
            continue
        out = smoke_test_lambda(arn, env, lambda_client=lambda_client, **inputs)
        score = out.get("score")
        if score != 1.0:
            raise RuntimeError(
                f"smoke-test for {ex} returned score={score!r} (expected 1.0); response={out}"
            )
        print(f"[lambda] {ex}: smoke-test score=1.0  ok")
        arns[ex] = arn
    return arns


# ---------------------------------------------------------------------------
# 3. Template helpers (ported verbatim from template_utils.py)
# ---------------------------------------------------------------------------

_VAR_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_DOUBLE_BRACE_BLOCK = re.compile(r"\{\{([^{}]*)\}\}")
_SINGLE_BRACE_VARIABLE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def to_service_format(template: str, fields: list[str]) -> str:
    """Convert a `str.format`-style template to APO double-brace format.

    Preserves literal `{`/`}` in JSON-style example bodies.
    """
    out = template
    markers: list[tuple[str, str]] = []
    for var in fields:
        marker = f"\x00FIELD{len(markers)}\x01"
        markers.append((marker, var))
        out = re.sub(r"\{\{?" + re.escape(var) + r"\}?\}", marker, out)
    out = out.replace("{{", "{").replace("}}", "}")
    for marker, var in markers:
        out = out.replace(marker, "{{" + var + "}}")
    return out


def validate_service_template(template: str) -> None:
    """Raise ValueError if the template would be rejected by the service."""
    remainder_parts: list[str] = []
    last = 0
    for m in _DOUBLE_BRACE_BLOCK.finditer(template):
        remainder_parts.append(template[last:m.start()])
        inner = m.group(1)
        if not _VAR_NAME.match(inner):
            raise ValueError(
                f"Malformed placeholder '{{{{ {inner!r} }}}}'. "
                "Variable names must match [a-zA-Z_][a-zA-Z0-9_]*."
            )
        last = m.end()
    remainder_parts.append(template[last:])
    sm = _SINGLE_BRACE_VARIABLE.search("".join(remainder_parts))
    if sm:
        raise ValueError(
            f"Single-brace placeholder '{{{sm.group(1)}}}' detected; use "
            f"'{{{{{sm.group(1)}}}}}' instead."
        )


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# 4. Per-example metadata + sample mapper
# ---------------------------------------------------------------------------

# Each entry captures: template variable names, the metric/result label, the
# input-key path on S3, and (multimodal only) the assets prefix and file-key
# in sample_data.jsonl.
EXAMPLES: dict[str, dict] = {
    # --- Lambda-metric mode -------------------------------------------------
    "nestful": {
        "mode": "lambda",
        "template_fields": ["tools", "user_question"],
        "metric_label": "nestful_partial_match",
        "template_id": "nestful_lambda_example",
        "multimodal": False,
    },
    "mmvqa": {
        "mode": "lambda",
        "template_fields": ["question"],
        "metric_label": "mmvqa_rouge_l",
        "template_id": "mmvqa_lambda_example",
        "multimodal": True,
        "asset_field": "document_path",
        "asset_type": "pdf",
        "asset_role": "document_path",
    },
    # --- LLM-as-Judge mode --------------------------------------------------
    "ifbench": {
        "mode": "llmj",
        "template_fields": ["prompt"],
        "metric_label": "ifbench_constraint_adherence",
        "template_id": "ifbench_llmj_example",
        "multimodal": False,
    },
    "defactify": {
        "mode": "llmj",
        "template_fields": ["caption"],
        "metric_label": "defactify_label_plus_emoji",
        "template_id": "defactify_llmj_example",
        "multimodal": True,
        "asset_field": "image_path",
        "asset_type": "image",
        "asset_role": "image_path",
    },
    # --- Steering mode ------------------------------------------------------
    "xsum": {
        "mode": "steering",
        "template_fields": ["document"],
        "template_id": "xsum_steer_example",
        "multimodal": False,
    },
    "mathvista": {
        "mode": "steering",
        "template_fields": ["question"],
        "template_id": "mathvista_steer_example",
        "multimodal": True,
        "asset_field": "image_path",
        "asset_type": "image",
        "asset_role": "image_path",
    },
    "spot": {
        "mode": "steering",
        "template_fields": ["message"],
        "template_id": "spot_local_optimization_example",
        "multimodal": False,
    },
}


def _assets_prefix(example: str) -> str:
    return f"{TUTORIAL_S3_PREFIX}/assets/{example}"


def _input_key(example: str) -> str:
    return f"{TUTORIAL_S3_PREFIX}/inputs/{example}.jsonl"


def _output_prefix(example: str, ts: str) -> str:
    return f"{TUTORIAL_S3_PREFIX}/outputs/{example}_{ts}"


def _load_samples(example: str, bucket: str, n_samples: int) -> list[dict]:
    """Build the per-sample `evaluationSamples[]` list for *example*."""
    meta = EXAMPLES[example]
    src = DATA_ROOT / example / "sample_data.jsonl"
    samples: list[dict] = []
    with src.open() as f:
        for i, line in enumerate(f):
            if i >= n_samples:
                break
            r = json.loads(line)
            entry: dict = {"inputVariables": [_input_variables(example, r)]}
            if meta["multimodal"]:
                file_name = Path(r[meta["asset_field"]]).name
                entry["inputVariablesMultimodal"] = [{
                    meta["asset_role"]: {
                        "type": meta["asset_type"],
                        "s3Uri": f"s3://{bucket}/{_assets_prefix(example)}/{file_name}",
                    },
                }]
            entry["referenceResponse"] = _reference_response(r)
            samples.append(entry)
    return samples


def _input_variables(example: str, r: dict) -> dict:
    """Return the inputVariables dict for one sample, with per-example quirks."""
    if example == "nestful":
        # tools may be a list -> serialize as JSON
        tools = r["tools"]
        return {
            "tools": tools if isinstance(tools, str) else json.dumps(tools),
            "user_question": r["user_question"],
        }
    # For all other examples, the sample fields exactly match the template fields.
    fields = EXAMPLES[example]["template_fields"]
    return {k: r[k] for k in fields}


def _reference_response(r: dict) -> str:
    gold = r["gold"]
    return gold if isinstance(gold, str) else json.dumps(gold)


# ---------------------------------------------------------------------------
# 5. Record builders (one per mode)
# ---------------------------------------------------------------------------

def _base_record(example: str, bucket: str, n_samples: int) -> dict:
    meta = EXAMPLES[example]
    template_text = (DATA_ROOT / example / "prompt_template.txt").read_text()
    template = to_service_format(template_text, fields=meta["template_fields"])
    validate_service_template(template)
    return {
        "version": API_VERSION,
        "templateId": meta["template_id"],
        "promptTemplate": template,
        "evaluationSamples": _load_samples(example, bucket, n_samples),
    }


def build_lambda_record(example: str, *, lambda_arn: str, bucket: str,
                        n_samples: int = N_SAMPLES_DEFAULT) -> dict:
    """Lambda-metric record. Sets evaluationMetricLambdaArn + customEvaluationMetricLabel."""
    if EXAMPLES[example]["mode"] != "lambda":
        raise ValueError(f"{example!r} is not a lambda-mode example.")
    record = _base_record(example, bucket, n_samples)
    record["evaluationMetricLambdaArn"] = lambda_arn
    record["customEvaluationMetricLabel"] = EXAMPLES[example]["metric_label"]
    return record


def build_llmj_record(example: str, *, rubric: str, judge_model_id: str, bucket: str,
                      n_samples: int = N_SAMPLES_DEFAULT) -> dict:
    """LLM-as-Judge record. Sets customLLMJConfig + customEvaluationMetricLabel."""
    if EXAMPLES[example]["mode"] != "llmj":
        raise ValueError(f"{example!r} is not an llmj-mode example.")
    record = _base_record(example, bucket, n_samples)
    record["customLLMJConfig"] = {
        "customLLMJPrompt": rubric,
        "customLLMJModelId": judge_model_id,
    }
    record["customEvaluationMetricLabel"] = EXAMPLES[example]["metric_label"]
    return record


def build_steering_record(example: str, *, steering_criteria: list[str], bucket: str,
                          n_samples: int = N_SAMPLES_DEFAULT) -> dict:
    """Steering record. Sets steeringCriteria (≤5 strings); no metric label."""
    if EXAMPLES[example]["mode"] != "steering":
        raise ValueError(f"{example!r} is not a steering-mode example.")
    if len(steering_criteria) > 5:
        raise ValueError(f"Service caps steeringCriteria at 5; got {len(steering_criteria)}.")
    record = _base_record(example, bucket, n_samples)
    record["steeringCriteria"] = steering_criteria
    return record


# ---------------------------------------------------------------------------
# 6. S3 upload + asset sync
# ---------------------------------------------------------------------------

def upload_input(record: dict, example: str, env: dict, s3=None) -> str:
    """Write the record to data/<example>/prepared/input.jsonl and upload."""
    if s3 is None:
        _, s3, _ = make_clients(env)
    local_path = DATA_ROOT / example / "prepared" / "input.jsonl"
    write_jsonl(local_path, [record])
    key = _input_key(example)
    s3.upload_file(str(local_path), env["BUCKET"], key)
    uri = f"s3://{env['BUCKET']}/{key}"
    return uri


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_assets(example: str, env: dict, s3=None) -> str:
    """Upload everything under data/<example>/assets/ to the bucket.

    Idempotent: skips files whose ETag (= md5 for non-multipart) already matches.
    Returns the S3 prefix URI.
    """
    if s3 is None:
        _, s3, _ = make_clients(env)
    src_dir = DATA_ROOT / example / "assets"
    if not src_dir.exists():
        raise FileNotFoundError(f"No assets directory for {example}: {src_dir}")
    prefix = _assets_prefix(example)
    uploaded = skipped = 0
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        key = f"{prefix}/{path.name}"
        try:
            head = s3.head_object(Bucket=env["BUCKET"], Key=key)
            existing_etag = head["ETag"].strip('"')
            if existing_etag == _md5(path):
                skipped += 1
                continue
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey"):
                raise
        s3.upload_file(str(path), env["BUCKET"], key)
        uploaded += 1
    print(f"[assets] {example}: uploaded={uploaded} skipped={skipped}")
    return f"s3://{env['BUCKET']}/{prefix}"


# ---------------------------------------------------------------------------
# 7. Submit + poll + fetch
# ---------------------------------------------------------------------------

def submit_job(input_s3_uri: str, *, model_id: str, env: dict, example: str,
               bedrock=None) -> dict:
    """Create one APO job; return {jobArn, jobName, outputS3}."""
    if bedrock is None:
        bedrock, _, _ = make_clients(env)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_name = f"apo-tutorial-{example}-{ts}"
    output_prefix = _output_prefix(example, ts)
    output_uri = f"s3://{env['BUCKET']}/{output_prefix}/"
    resp = bedrock.create_advanced_prompt_optimization_job(
        jobName=job_name,
        modelConfigurations=[{"modelId": model_id}],
        inputConfig={"s3Uri": input_s3_uri},
        outputConfig={"s3Uri": output_uri},
    )
    return {"jobArn": resp["jobArn"], "jobName": job_name, "outputS3": output_uri}


def poll_job(job_arn: str, env: dict, *, poll_secs: int = 60,
             on_status: Callable[[str, float], None] | None = None,
             bedrock=None) -> dict:
    """Poll until terminal; invoke `on_status(status, elapsed_s)` every second.

    Hits the Bedrock API every `poll_secs` (default 60); fires the callback
    every second so an `elapsed` display ticks smoothly between API checks.
    """
    if bedrock is None:
        bedrock, _, _ = make_clients(env)
    start = time.time()
    next_poll_at = 0.0
    status = "Pending"
    info: dict = {}
    while True:
        elapsed = time.time() - start
        if elapsed >= next_poll_at:
            info = bedrock.get_advanced_prompt_optimization_job(jobIdentifier=job_arn)
            status = info.get("jobStatus", "")
            next_poll_at = elapsed + poll_secs
        if on_status is not None:
            on_status(status, elapsed)
        if status in ("Completed", "Failed", "Stopped"):
            return info
        time.sleep(1)


def download_results(job_info: dict, env: dict, local_path: Path, s3=None) -> Path:
    """Download the result JSONL emitted by the service."""
    if s3 is None:
        _, s3, _ = make_clients(env)
    bucket = env["BUCKET"]
    out_uri = job_info["outputConfig"]["s3Uri"].rstrip("/")
    job_id = job_info["jobArn"].rsplit("/", 1)[-1]
    out_key = f"{out_uri.split(f's3://{bucket}/', 1)[1]}/{job_id}/advanced_prompt_optimization_results.jsonl"
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, out_key, str(local_path))
    return local_path


def run_job(record: dict, *, example: str, model_id: str, env: dict,
            on_status: Callable[[str, float], None] | None = None,
            results_path: Path | None = None) -> Path:
    """End-to-end: upload → submit → poll → download. Returns path to result JSONL.

    Replay-mode escape hatch: when `APO_USE_REFERENCE=1`, returns the bundled
    `data/<example>/reference_results.jsonl` immediately without calling AWS.
    """
    if os.environ.get("APO_USE_REFERENCE") == "1":
        ref = DATA_ROOT / example / "reference_results.jsonl"
        if not ref.exists():
            raise FileNotFoundError(
                f"APO_USE_REFERENCE=1 but no bundled results for {example} at {ref}."
            )
        print(f"[run_job] APO_USE_REFERENCE=1 — using bundled {ref.name}")
        return ref

    bedrock, s3, _ = make_clients(env)
    input_uri = upload_input(record, example, env, s3=s3)
    job = submit_job(input_uri, model_id=model_id, env=env, example=example, bedrock=bedrock)
    print(f"[submit] {job['jobName']}  arn=…{job['jobArn'][-12:]}")
    info = poll_job(job["jobArn"], env, on_status=on_status, bedrock=bedrock)
    final_status = info.get("jobStatus", "")
    if final_status != "Completed":
        print(f"[run_job] terminal status: {final_status}")
    target = results_path or (DATA_ROOT / example / "results_live.jsonl")
    return download_results(info, env, target, s3=s3)


# ---------------------------------------------------------------------------
# 8. Results parsing
# ---------------------------------------------------------------------------

def parse_results(path: Path) -> list[dict]:
    """Flatten result JSONL into one dict per (template, model) result row.

    Result schema (current): top-level has `promptTemplateId`, `promptTemplate`,
    `customEvaluationMetricLabel`, `promptOptimizationResults[]`; per-result
    has `status`, `modelId`, `optimizedPromptTemplate`,
    `originalPromptMetrics.averageScore`, `optimizedPromptMetrics.averageScore`.
    """
    rows: list[dict] = []
    with Path(path).open() as f:
        for line in f:
            d = json.loads(line)
            base_template = d.get("promptTemplate")
            template_id = d.get("promptTemplateId") or d.get("templateId")
            for r in d.get("promptOptimizationResults", []):
                row = {
                    "templateId": template_id,
                    "metricLabel": d.get("customEvaluationMetricLabel"),
                    "status": r.get("status"),
                    "modelId": r.get("modelId"),
                    "original": (r.get("originalPromptMetrics") or {}).get("averageScore"),
                    "optimized": (r.get("optimizedPromptMetrics") or {}).get("averageScore"),
                    "originalTemplate": base_template,
                    "optimizedTemplate": r.get("optimizedPromptTemplate"),
                    "failureReason": r.get("failureReason"),
                }
                if row["original"] is not None and row["optimized"] is not None:
                    row["delta"] = row["optimized"] - row["original"]
                else:
                    row["delta"] = None
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 9. Markdown renderers (return IPython.display.Markdown)
# ---------------------------------------------------------------------------

_MODE_OVERVIEW = {
    "lambda": """
### Lambda metric — evaluator overview

You supply a single-file Python Lambda that scores model outputs. The service
sends `{"preds": [...], "golds": [...]}` and your handler returns
`{"score": float, "scores": [float, ...]}`. APO uses the aggregate score to
guide optimization.

**Required fields on each input record**

| Field | Required | Notes |
|---|---|---|
| `evaluationMetricLambdaArn` | ✅ | Function ARN |
| `customEvaluationMetricLabel` | ✅ | Label that shows up in result JSON |
| `promptTemplate` | ✅ | Uses `{{var}}` placeholders |
| `evaluationSamples[]` | ✅ | Each with `inputVariables` + `referenceResponse` |

**When to use:** you have a programmable, deterministic metric (exact match,
ROUGE, F1, partial credit). Strict-mode AST scan limits imports to a vetted
allowlist (stdlib + numpy/scipy/pandas/sklearn/nltk/rouge_score/sacrebleu/
evaluate/rapidfuzz/editdistance/jiwer/regex/transformers/torch/
sentence_transformers/bert_score). No `os`, `subprocess`, `open`, etc.
""",
    "llmj": """
### LLM-as-Judge — evaluator overview

A judge model scores each response according to a natural-language rubric you
author. No Lambda needed.

**Required fields on each input record**

| Field | Required | Notes |
|---|---|---|
| `customLLMJConfig.customLLMJPrompt` | ✅ | The rubric body |
| `customLLMJConfig.customLLMJModelId` | ✅ | The judge model id |
| `customEvaluationMetricLabel` | ✅ | Label in result JSON |
| `promptTemplate` | ✅ | Optimized prompt |
| `evaluationSamples[]` | ✅ | Each with `inputVariables` + `referenceResponse` |

**Gotcha (brace escaping):** the harness `str.format`s the rubric with
`{prompt}, {prediction}, {gold}`. Literal `{`/`}` inside the rubric must be
escaped as `{{`/`}}` or the format call raises KeyError and the harness
silently scores 0.0 on every sample.

**When to use:** subjective quality, perceptual judgment, criteria that are
easier to describe than to compute.
""",
    "steering": """
### Steering criteria — evaluator overview

Instead of a Lambda or judge, you give the optimizer a list of natural-language
rules. The optimizer's internal scorer enforces them.

**Required fields on each input record**

| Field | Required | Notes |
|---|---|---|
| `steeringCriteria` | ✅ | List of ≤5 plain-English rules |
| `promptTemplate` | ✅ | Optimized prompt |
| `evaluationSamples[]` | ✅ | Each with `inputVariables` + `referenceResponse` |

**When to use:** no clean numeric metric, no ground-truth comparison desired
— you just want to shape the output format / structure / tone. Lowest setup
friction of the three modes (no Lambda, no rubric).
""",
}


def render_mode_overview(mode: str) -> Markdown:
    """Concept paragraph + field-matrix table + when-to-use rule of thumb."""
    if mode not in _MODE_OVERVIEW:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {list(_MODE_OVERVIEW)}.")
    return Markdown(_MODE_OVERVIEW[mode].strip())


def _truncate(value: object, max_chars: int) -> str:
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + " …"


def _escape_md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ↵ ")


def render_sample_shape(record: dict, *, max_chars: int = 240) -> Markdown:
    """First sample's fields as a Markdown table; long values truncated."""
    samples = record.get("evaluationSamples", [])
    if not samples:
        return Markdown("*(no samples)*")
    s = samples[0]
    lines = ["| Field | Value (truncated) |", "|---|---|"]
    iv = s.get("inputVariables", [{}])[0]
    for k, v in iv.items():
        lines.append(f"| `inputVariables[0].{k}` | {_escape_md(_truncate(v, max_chars))} |")
    if "inputVariablesMultimodal" in s:
        mm = s["inputVariablesMultimodal"][0]
        role, payload = next(iter(mm.items()))
        lines.append(
            f"| `inputVariablesMultimodal[0].{role}` | type=`{payload['type']}` "
            f"s3Uri=`{_escape_md(payload['s3Uri'])}` |"
        )
    lines.append(f"| `referenceResponse` | {_escape_md(_truncate(s.get('referenceResponse', ''), max_chars))} |")
    return Markdown("\n".join(lines))


def render_record_shape(record: dict) -> Markdown:
    """Top-level record fields with one-line summaries."""
    fields_present = []
    rules = {
        "evaluationMetricLambdaArn": "Lambda mode",
        "customLLMJConfig": "LLM-as-Judge mode",
        "steeringCriteria": "Steering mode",
    }
    active_mode = None
    for k, label in rules.items():
        if k in record:
            active_mode = label
            fields_present.append(k)
    lines = ["| Field | Type | Notes |", "|---|---|---|"]
    lines.append(f"| `version` | str | `{record.get('version')}` |")
    lines.append(f"| `templateId` | str | `{record.get('templateId')}` |")
    lines.append(f"| `promptTemplate` | str (with `{{{{var}}}}`) | {len(record.get('promptTemplate',''))} chars |")
    if "customEvaluationMetricLabel" in record:
        lines.append(f"| `customEvaluationMetricLabel` | str | `{record['customEvaluationMetricLabel']}` |")
    if "evaluationMetricLambdaArn" in record:
        arn = record["evaluationMetricLambdaArn"]
        lines.append(f"| `evaluationMetricLambdaArn` | str | …{arn[-40:]} |")
    if "customLLMJConfig" in record:
        cfg = record["customLLMJConfig"]
        lines.append(f"| `customLLMJConfig.customLLMJModelId` | str | `{cfg.get('customLLMJModelId')}` |")
        lines.append(f"| `customLLMJConfig.customLLMJPrompt` | str | {len(cfg.get('customLLMJPrompt',''))} chars |")
    if "steeringCriteria" in record:
        lines.append(f"| `steeringCriteria` | list[str] | {len(record['steeringCriteria'])} rules |")
    n = len(record.get("evaluationSamples", []))
    lines.append(f"| `evaluationSamples` | list[obj] | {n} samples |")
    mode_note = f"\n\n**Active mode:** `{active_mode}` (at-most-one rule satisfied)." if active_mode else ""
    return Markdown("\n".join(lines) + mode_note)


def render_dimensions(record: dict, n_iterations: int = 5) -> Markdown:
    """Templates × samples × iterations summary table."""
    n_templates = 1  # one record per JSONL line in this tutorial
    n_samples = len(record.get("evaluationSamples", []))
    total = n_templates * n_samples * (n_iterations + 1)  # +1 for baseline
    return Markdown(
        "| Dimension | Value |\n"
        "|---|---|\n"
        f"| Prompt templates (this job) | **{n_templates}** |\n"
        f"| Evaluation samples per template | **{n_samples}** |\n"
        f"| Optimization iterations | **{n_iterations}** (service default) |\n"
        f"| Total scoring events ≈ | **{total}** (samples × (iters + baseline)) |"
    )


def render_results_table(parsed: list[dict]) -> Markdown:
    """Original vs optimized scores, one row per (template, model)."""
    if not parsed:
        return Markdown("*(no results)*")
    lines = ["| templateId | modelId | status | original | optimized | Δ | failureReason |",
             "|---|---|---|---:|---:|---:|---|"]
    for r in parsed:
        orig = f"{r['original']:.4f}" if r['original'] is not None else "—"
        opt = f"{r['optimized']:.4f}" if r['optimized'] is not None else "—"
        delta = f"**{r['delta']:+.4f}**" if r['delta'] is not None else "—"
        fr = _escape_md(_truncate(r.get("failureReason") or "", 80))
        lines.append(
            f"| `{r['templateId']}` | `{r['modelId']}` | `{r['status']}` "
            f"| {orig} | {opt} | {delta} | {fr} |"
        )
    return Markdown("\n".join(lines))


def render_prompt_diff(parsed_row: dict) -> Markdown:
    """Collapsible original vs optimized template sections."""
    orig = parsed_row.get("originalTemplate") or "(not present)"
    opt = parsed_row.get("optimizedTemplate") or "(not present)"
    return Markdown(
        f"<details><summary><b>Original template</b> ({len(orig)} chars)</summary>\n\n"
        f"```\n{orig}\n```\n</details>\n\n"
        f"<details open><summary><b>Optimized template</b> ({len(opt)} chars)</summary>\n\n"
        f"```\n{opt}\n```\n</details>"
    )
