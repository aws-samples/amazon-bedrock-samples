import os
import time
import concurrent.futures
import json
import logging
import pandas as pd
import argparse
from dotenv import load_dotenv
from datetime import datetime
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from visualize_results import create_html_report
from utils import (run_3p_inference,
                    get_timestamp,
                   setup_logging,
                   calculate_average_scores,
                   converse_with_bedrock,
                   extract_json_response,
                   llm_judge_template,
                   get_body)

env = load_dotenv()


# ----------------------------------------
# Single LLM‑as‑judge call
# ----------------------------------------
def evaluate_with_llm_judge(judge_model_id,
                            judge_region,
                            prompt,
                            model_response,
                            golden_answer,
                            task_types,
                            task_criteria,
                            custom_metrics=None
                            ):
    """
     Runs the target model on `prompt`, then has three jury models
     evaluate its response against `golden_response` using the
     specified metrics. Returns per-juror scores, aggregated scores,
     and a final pass/fail decision by majority vote.
     """
    standard_metrics = ["Correctness", "Completeness", "Relevance", "Format", "Coherence", "Following-instructions"]
    all_metrics = standard_metrics + (custom_metrics or [])

    eval_template = llm_judge_template(all_metrics,
                                       task_types,
                                       task_criteria,
                                       prompt,
                                       model_response,
                                       golden_answer)

    body = [{"role": "user", "content": [{"text": eval_template}]}]
    cfg = {"maxTokens": 750, "temperature": 0.3, "topP": 0.9}

    try:
        resp, ignore, ignore  = converse_with_bedrock(messages=body,
                                        model_id=judge_model_id,
                                        region=judge_region,
                                        inference_config=cfg,
                                        stream=False)
        text = resp['output']['message']['content'][0]['text']
    except Exception as e:
        logging.error(f"Judge error ({judge_model_id}): {e}")
        return {"judgment": "Error inference response", "explanation": str(e), "full_response": "", "scores": {"score": "NULL"}}

    try:
        eval_results = extract_json_response(all_metrics, text, judge_model_id, judge_region, cfg)
        if not eval_results:
            return {"judgment": "Error Parsing response", "explanation": "JSON NOT FOUND", "full_response": text,
                    "scores": {"score": "NULL"}}

        judgment = "PASS"
        explanation = [key for key, val in eval_results["scores"].items() if val < 3]
        if len(explanation) > 0:
            judgment = "FAIL"

        eval_results["judgment"] = judgment
        payload = {
            "judgment": eval_results["judgment"],
            "scores": eval_results["scores"],
            "explanation": ";".join(explanation),
            "full_response": text,
            "judge_input_tokens": resp['usage']['inputTokens'],
            "judge_output_tokens": resp['usage']['outputTokens']
        }
    except Exception as e:
        return {"judgment": "Error Parsing response", "explanation": str(e), "full_response": text, "scores": {"score": "NULL"}}

    return payload

# ----------------------------------------
# Multi‑judge + majority‑vote
# ----------------------------------------
def evaluate_with_judges(judges,
                         prompt,
                         model_response,
                         golden_answer,
                         task_types,
                         task_criteria,
                        user_defined_metrics
                         ):

    results = []
    for j in judges:
        r = evaluate_with_llm_judge(
            judge_model_id=j["model_id"],
            judge_region=j["region"],
            prompt=prompt,
            model_response=model_response,
            golden_answer=golden_answer,
            task_types=task_types,
            task_criteria=task_criteria,
            custom_metrics=user_defined_metrics
        )
        r['judge_input_token_cost'] = r["judge_input_tokens"] * (j["input_cost_per_1k"] / 1000) # After 15 years I still don't trust the order of operators :)
        r['judge_output_token_cost'] = r["judge_output_tokens"] * (j["output_cost_per_1k"] / 1000)
        results.append({"model": j["model_id"], **r})


    pass_ct = sum(1 for r in results if r["judgment"] == "PASS")
    fail_ct = sum(1 for r in results if r["judgment"] == "FAIL")
    tot_cost = sum(r["judge_input_token_cost"] + r['judge_output_token_cost'] for r in results )

    avg_scores = calculate_average_scores([result['scores'] for result in results])
    maj     = "PASS" if pass_ct > fail_ct else "FAIL"
    exps    = [r["explanation"] for r in results if r["judgment"] == maj]
    return {"majority_judgment": maj, "majority_explanations": exps, "judge_details": results, "majority_score": avg_scores, "eval_cost": tot_cost}


def run_bedrock_inference(
        region=None,
        prompt=None,
        latency_profile=None,
        max_tokens=None,
        model_id=None,
        in_cost=None,
        out_cost=None,
        temperature=0,
        top_p=0,
    ):

        throughput_tps = None
        ttlb = None
        ttfb = None
        out_toks = None
        resp_txt = ""
        in_toks = None
        cost = None

        # build messages
        msgs, cfgs = get_body(prompt, max_tokens, temperature, top_p)
        r, start, request_count = converse_with_bedrock(
            region=region,
            messages=msgs,
            model_id=model_id,
            inference_config=cfgs,
            perf_config={"latency": latency_profile})
        first = None
        for ev in r.get("stream", []):
            if "contentBlockDelta" in ev:
                d = ev["contentBlockDelta"].get("delta", {})
                if "text" in d:
                    resp_txt += d["text"]
                    if first is None:
                        first = time.time()
            elif "metadata" in ev and ev["metadata"].get("usage"):
                u = ev["metadata"]["usage"]
                out_toks = u.get("outputTokens")
                in_toks = u.get("inputTokens")
                if in_toks is not None and out_toks is not None:
                    cost = in_toks * in_cost + out_toks * out_cost
        end = time.time()
        if first:
            ttfb = round(first - start, 4)
            ttlb = round(end - start, 4)
        if ttlb and out_toks:
            throughput_tps = round(out_toks / ttlb, 2)

        return {"throughput_tps":throughput_tps,
                "time_to_first_byte": ttfb,
                "time_to_last_byte": ttlb,
                "input_tokens": in_toks,
                "output_tokens": out_toks,
                "response_cost": cost,
                "model_response": resp_txt,
                "request_count": request_count}

# ----------------------------------------
# Core benchmarking function
# ----------------------------------------
def benchmark(
        region,
        prompt, task_types, task_criteria, golden_answer,
        latency_profile, max_tokens, model_id,
        in_cost, out_cost,
        temperature, top_p,
        judge_models,
        user_defined_metrics
):
    logging.debug(f"Starting benchmark for model: {model_id} in region: {region}")
    status   = "Success"
    ts       = get_timestamp()
    perf     = {}
    err_code = None
    time_to_first_byte = None
    time_to_last_byte = None
    input_tokens = None
    output_tokens = None
    cost = None
    resp_txt = None
    evaluation_cost_data = 0
    inference_request_count = 0
    throughput_tps = 0
    try:
        if '/' in model_id:
            r = run_3p_inference(model_id,
                             prompt,
                             provider_params={"api_key": os.getenv('OPENAI_API'),
                                              "max_tokens": max_tokens,
                                              "temperature": temperature,
                                              "top_p": top_p})

            time_to_first_byte = r['time_to_first_byte']
            time_to_last_byte = r['time_to_last_byte']
            input_tokens = r['input_tokens']
            output_tokens = r['output_tokens']
            cost = r['response_cost']
            resp_txt = r['model_response']
        else:
            r = run_bedrock_inference(
                region,
                prompt,
                latency_profile,
                max_tokens,
                model_id,
                in_cost,
                out_cost,
                temperature,
                top_p)

            time_to_first_byte = r['time_to_first_byte']
            time_to_last_byte = r['time_to_last_byte']
            input_tokens = r['input_tokens']
            output_tokens = r['output_tokens']
            cost = r['response_cost']
            resp_txt = r['model_response']
            inference_request_count = r['request_count']
            throughput_tps = r['throughput_tps']

        if resp_txt:
            multi = evaluate_with_judges(
                judge_models,
                prompt,
                resp_txt,
                golden_answer,
                task_types,
                task_criteria,
                user_defined_metrics
            )
            perf["judge_success"]     = (multi["majority_judgment"] == "PASS")
            perf["judge_explanation"] = ";".join(list(set(multi["majority_explanations"])))
            perf["judge_details"]     = multi["judge_details"]
            perf["judge_scores"]      = multi["majority_score"]
            evaluation_cost_data   = multi["eval_cost"]
        else:
            status = "LLM-AS-A-JURY EVALUATION ERROR"
            logging.error(f"Unexpected error evaluating {model_id}: {status}")

    except ClientError as err:
        status = err.response["Error"]["Code"]
        status += f" {str(err)}"
        logging.error(f"API error evaluating {model_id}: {status}")
    except Exception as e:
        status = str(e)
        logging.error(f"Unexpected error evaluating {model_id}: {status}")

    return {
        "time_to_first_byte":  time_to_first_byte,
        "time_to_last_byte":   time_to_last_byte,
        "throughput_tps":      throughput_tps,
        "job_timestamp_iso":   ts,
        "api_call_status":     status,
        "error_code":          err_code,
        "input_tokens":        input_tokens,
        "output_tokens":       output_tokens,
        "response_cost":       cost,
        "model_response":      resp_txt,
        "performance_metrics": perf,
        "evaluation_cost":     evaluation_cost_data,
        "inference_request_count": inference_request_count
    }

# ----------------------------------------
# Scenario expansion: dynamic temp sweeps
# ----------------------------------------
def expand_scenarios(raw, cfg):
    expanded = []
    for s in raw:
        prompt = s["prompt"]
        region = s["region"]
        base_t = s.get("TEMPERATURE", cfg["TEMPERATURE"])
        param_variants = []
        n_variants = cfg["TEMPERATURE_VARIATIONS"]
        u_diff = 1
        l_diff = 1
        for _ in range(0, n_variants + 1):
            param_variants.append(round(base_t * u_diff, 3))
            param_variants.append(round(base_t * l_diff, 3))
            u_diff += .25
            l_diff -= .25
        # build ±10% and ±20% around base
        temps = sorted(set(param_variants))
        for t in temps:
            if t <= 1:
                sc = s.copy()
                sc["prompt"] = prompt
                sc["region"] = region
                sc["TEMPERATURE"]  = round(t, 3)
                expanded.append(sc)
    return expanded

# ----------------------------------------
# Parallel execution
# ----------------------------------------
def execute_benchmark(_, scenarios, cfg, unprocessed_dir):
    all_recs = []
    unprocessed_records = []
    lock = Lock()
    
    def run_scn(scn):
        recs = []
        local_unprocessed = []
        
        for invocation in range(cfg["invocations_per_scenario"]):
            try:
                logging.info(f"Running scenario: {scn['model_id']}@{scn['region']}, temp={scn['TEMPERATURE']}, invocation {invocation+1}/{cfg['invocations_per_scenario']}")
                r = benchmark(
                    scn["region"],
                    scn["prompt"],
                    scn["task_types"],
                    scn["task_criteria"],
                    scn["golden_answer"],
                    scn["inference_profile"],
                    scn["configured_output_tokens_for_request"],
                    scn["model_id"],
                    scn["input_token_cost"] / 1000,
                    scn["output_token_cost"] / 1000,
                    scn["TEMPERATURE"],
                    cfg["TOP_P"],
                    cfg["judge_models"],
                    cfg["user_defined_metrics"]
                )
                
                # Check if the record was processed successfully
                if r["api_call_status"] != "Success" or r["error_code"] is not None:
                    logging.warning(f"Record processing failed: {scn['model_id']}@{scn['region']}, error: {r['error_code']}")
                    local_unprocessed.append({"scenario": scn, "result": r, "reason": f"API error: {r['error_code']}"}) 
                else:
                    recs.append({**scn, **r})
                    logging.debug(f"Successfully processed: {scn['model_id']}@{scn['region']}, invocation {invocation+1}")
            except Exception as e:
                error_msg = f"Exception processing record: {str(e)}"
                logging.error(error_msg)
                local_unprocessed.append({"scenario": scn, "exception": str(e), "reason": "Exception during processing"})
                
            if cfg["sleep_between_invocations"]:
                time.sleep(cfg["sleep_between_invocations"])
        
        with lock:
            logging.info(f"Completed scenario: {scn['model_id']}@{scn['region']} temp={scn['TEMPERATURE']}, processed: {len(recs)}, failed: {len(local_unprocessed)}")
            if local_unprocessed:
                unprocessed_records.extend(local_unprocessed)
        
        return recs

    with ThreadPoolExecutor(max_workers=cfg["parallel_calls"]) as exe:
        futures = [exe.submit(run_scn, s) for s in scenarios]
        for f in concurrent.futures.as_completed(futures):
            all_recs.extend(f.result())
    
    # Write unprocessed records to file if any exist
    if unprocessed_records:
        ts = get_timestamp().replace(':', '-')
        unprocessed_file = os.path.join(unprocessed_dir, f"unprocessed_{ts}.json")
        logging.warning(f"Writing {len(unprocessed_records)} unprocessed records to {unprocessed_file}")
        with open(unprocessed_file, 'w') as f:
            json.dump(unprocessed_records, f, indent=2, default=str)
            
    return all_recs

# ----------------------------------------
# Main entrypoint
# ----------------------------------------
def main(
    input_file,
    output_dir,
    parallel_calls,
    invocations_per_scenario,
    sleep_between_invocations,
    temp_variants,
    experiment_counts,
    experiment_name,
    defined_metrics
):
    user_defined_metrics = None
    if defined_metrics:
        user_defined_metrics = [metrics.strip().replace(' ', '-') for metrics in defined_metrics.split(',')]

    # Create logs directory
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Setup logging
    ts, log_file = setup_logging(logs_dir)
    logging.info(f"Starting benchmark run: {experiment_name}")
    print(f"Logs are being saved to: {log_file}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create directory for unprocessed records
    unprocessed_dir = os.path.join(output_dir, "unprocessed")
    os.makedirs(unprocessed_dir, exist_ok=True)

    eval_dir = "./prompt-evaluations"
    file_path = os.path.join(eval_dir, input_file)
    judges_list = []
    judge_file_name = "judge_profiles.jsonl"
    model_file_name = "model_profiles.jsonl"
    judge_path = os.path.join(eval_dir, judge_file_name)
    model_path = os.path.join(eval_dir, model_file_name)
    with open(judge_path, 'r', encoding='utf-8') as f:
        for line in f:
            judges_list.append(json.loads(line))

    cfg = {
        "parallel_calls":                parallel_calls,
        "invocations_per_scenario":      invocations_per_scenario,
        "sleep_between_invocations":     sleep_between_invocations,
        "TEMPERATURE":                   1.0,
        "TEMPERATURE_VARIATIONS":        int(temp_variants),
        "TOP_P":                         1.0,
        "EXPERIMENT_NAME":               experiment_name,
        "judge_models":                  judges_list,
        "user_defined_metrics":          user_defined_metrics
    }

    # Load scenarios
    raw = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            js = json.loads(line)
            raw.append({
                "prompt":                               js.get("text_prompt", ""),
                "task_types":                           js["task"]["task_type"],
                "task_criteria":                        js["task"]["task_criteria"],
                "golden_answer":                        js.get("golden_answer", ""),
                "configured_output_tokens_for_request": js.get("expected_output_tokens",200),
                "region":                               js.get("region", "us-east-1"),
            })
    if not raw:
        logging.error("No scenarios found in input.")
        return
    
    raw_with_models = []
    with open(model_path, 'r', encoding='utf-8') as f:
        for line in f:
            js = json.loads(line)
            for s in raw:
                raw_with_models.append({**s, **js})                

    scenarios = expand_scenarios(raw_with_models, cfg)
    logging.info(f"Expanded to {len(scenarios)} scenarios")

    all_dfs = []
    for run in range(1, experiment_counts+1):
        logging.info(f"=== Run {run}/{experiment_counts} ===")
        results = execute_benchmark(None, scenarios, cfg, unprocessed_dir)
        
        if not results:
            logging.error(f"Run {run}/{experiment_counts} produced no results. Check the unprocessed records file.")
            continue
            
        df = pd.DataFrame(results)
        df["run_count"] = run
        df["timestamp"] = pd.Timestamp.now()
        out_csv = os.path.join(output_dir, f"invocations_{run}_{ts}.csv")
        df.to_csv(out_csv, index=False)
        logging.info(f"Run {run} results saved to {out_csv}")
        all_dfs.append(df)

    master = pd.concat(all_dfs, ignore_index=True)

    # # Latency percentiles
    # lat = master["time_to_last_byte"].dropna()
    # pct = {f"p{p}": np.percentile(lat,p) for p in (50, 90, 95, 99)}
    # print("Latency percentiles:", pct)
    # logging.info(f"Percentiles: {pct}")

    # Cost summary & monthly forecast
    cost_sum = (
        master
        .groupby(["model_id","inference_profile"])["response_cost"]
        .agg(["mean","sum","count"])
        .rename(columns={"mean":"avg_cost","sum":"total_cost","count":"num_invocations"})
    )
    cost_sum["monthly_forecast"] = (
        cost_sum["avg_cost"] *
        (cost_sum["num_invocations"] / invocations_per_scenario) * 30
    )
    print("\nCost summary & forecast:\n", cost_sum)

    logging.info(f"Cost summary:\n{cost_sum}")

    # Generate report
    report = create_html_report(output_dir, ts)
    
    # Check for unprocessed records
    unprocessed_files = [f for f in os.listdir(unprocessed_dir) if f.startswith("unprocessed_")]
    if unprocessed_files:
        logging.warning(f"Found {len(unprocessed_files)} files with unprocessed records in {unprocessed_dir}")
        print(f"\nWarning: {len(unprocessed_files)} files with unprocessed records found in {unprocessed_dir}")
    
    print(f"\nBenchmark complete! Report: {report}")
    logging.info(f"Benchmark run complete. Report generated at {report}")




if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Advanced Unified LLM Benchmarking Tool")
    p.add_argument("input_file",                  help="JSONL file with scenarios")
    p.add_argument("--output_dir",                default="./benchmark_results")
    p.add_argument("--parallel_calls",            type=int, default=4)
    p.add_argument("--invocations_per_scenario",  type=int, default=2)
    p.add_argument("--sleep_between_invocations", type=int, default=3)
    p.add_argument("--experiment_counts",         type=int, default=2)
    p.add_argument("--experiment_name",           default=f"Benchmark-{datetime.now().strftime('%Y%m%d')}")
    p.add_argument("--temperature_variations",    type=int, default=0)
    p.add_argument("--user_defined_metrics",      default=None)
    args = p.parse_args()

    main(
        args.input_file,
        args.output_dir,
        args.parallel_calls,
        args.invocations_per_scenario,
        args.sleep_between_invocations,
        args.temperature_variations,
        args.experiment_counts,
        args.experiment_name,
        args.user_defined_metrics
    )

