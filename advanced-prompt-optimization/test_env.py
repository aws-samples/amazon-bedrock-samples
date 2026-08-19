"""Smoke test for the APO us-west-2 environment.

Runs a tiny end-to-end steering-mode job on the xsum sample (text-only, no
Lambda or judge model needed). Confirms: IAM perms, bucket access, bedrock
client config, and that CreateAdvancedPromptOptimizationJob is accepted.
"""

from __future__ import annotations

import sys
import time

import utils

EXAMPLE = "xsum"
TARGET_MODEL_ID = "us.anthropic.claude-opus-4-6-v1"
N_SAMPLES = 3
STEERING_CRITERIA = [
    "Summary should be a single concise sentence.",
    "Summary should preserve the key factual subject of the article.",
]


def main() -> int:
    env = utils.load_env()
    print(f"[env] REGION={env['REGION']}  BUCKET={env['BUCKET']}")
    print(f"[env] TARGET_MODEL_ID={TARGET_MODEL_ID}")

    record = utils.build_steering_record(
        EXAMPLE,
        steering_criteria=STEERING_CRITERIA,
        bucket=env["BUCKET"],
        n_samples=N_SAMPLES,
    )
    print(f"[record] templateId={record['templateId']}  samples={len(record['evaluationSamples'])}")

    start = time.time()

    def on_status(status: str, elapsed: float) -> None:
        print(f"[poll] t={elapsed:6.0f}s  status={status}")

    results_path = utils.run_job(
        record,
        example=EXAMPLE,
        model_id=TARGET_MODEL_ID,
        env=env,
        on_status=on_status,
    )

    print(f"[done] elapsed={time.time() - start:.0f}s  results={results_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
