import os
import time
import concurrent.futures
import json
import logging
import uuid
import pandas as pd
import argparse
from dotenv import load_dotenv
from datetime import datetime
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from utils import (get_timestamp,
                   setup_logging,
                   calculate_average_scores,
                   run_inference,
                   extract_json_response,
                   llm_judge_template)

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
                            custom_metrics=None,
                            yard_stick=3):
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

    cfg = {"maxTokens": 1500, "temperature": 0.3, "topP": 0.9, "aws_region_name": judge_region}
    try:
        resp = run_inference(model_name=judge_model_id,
                             prompt_text=eval_template,
                             provider_params=cfg,
                             stream=False)
        text = resp['text']
    except Exception as e:
        logging.error(f"Judge error ({judge_model_id}): {e}")
        return {"judgment": "Error inference response", "explanation": str(e), "full_response": "", "scores": {"score": "NULL"}}

    try:
        eval_results = extract_json_response(all_metrics, text, judge_model_id, cfg)
        if not eval_results:
            return {"judgment": "Error Parsing response", "explanation": "JSON NOT FOUND", "full_response": text,
                    "scores": {"score": "NULL"}}

        judgment = "PASS"
        explanation = [key for key, val in eval_results["scores"].items() if val < yard_stick]
        if len(explanation) > 0:
            judgment = "FAIL"

        eval_results["judgment"] = judgment
        payload = {
            "judgment": eval_results["judgment"],
            "scores": eval_results["scores"],
            "explanation": ";".join(explanation),
            "full_response": text,
            "judge_input_tokens": resp['inputTokens'],
            "judge_output_tokens": resp['outputTokens']
        }
    except Exception as e:
        logging.error(f"Error when evaluation with {judge_model_id}: {e}")
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
                         user_defined_metrics,
                         yard_stick=3):

    results = []
    for j in judges:
        try:
            logging.debug(f"Evaluating with judge model {j['model_id']}")
            r = evaluate_with_llm_judge(
                judge_model_id=j["model_id"],
                judge_region=j["region"],
                prompt=prompt,
                model_response=model_response,
                golden_answer=golden_answer,
                task_types=task_types,
                task_criteria=task_criteria,
                custom_metrics=user_defined_metrics,
                yard_stick = yard_stick
            )
            
            # Check for various error indicators
            if "error" in r or r.get("judgment") == "Error inference response" or r.get("judgment") == "Error Parsing response":
                logging.warning(f"Judge {j['model_id']} returned an error response: {r.get('explanation', 'Unknown error')}")
                results.append({"model": j["model_id"], **r})
                continue
                
            # Check if scores are valid
            if not r.get("scores") or r.get("scores", {}).get("score") == "NULL":
                logging.warning(f"Judge {j['model_id']} returned invalid scores: {r.get('scores', 'None')}")
                results.append({"model": j["model_id"], **r})
                continue
                
            r['judge_input_token_cost'] = r["judge_input_tokens"] * (j["input_cost_per_1k"] / 1000) # After 15 years I still don't trust the order of operators :)
            r['judge_output_token_cost'] = r["judge_output_tokens"] * (j["output_cost_per_1k"] / 1000)
            results.append({"model": j["model_id"], **r})
            logging.debug(f"Successfully evaluated with judge {j['model_id']}, judgment: {r.get('judgment', 'Unknown')}")
        except Exception as e:
            logging.error(f"Exception evaluating with judge {j['model_id']}: {str(e)}", exc_info=True)
            results.append({"model": j["model_id"], "judgment": "Judge Exception", "explanation": str(e), "scores": {"score": "NULL"}})


    pass_ct = sum(1 for r in results if r["judgment"] == "PASS")
    fail_ct = sum(1 for r in results if r["judgment"] == "FAIL")
    tot_cost = sum(r["judge_input_token_cost"] + r['judge_output_token_cost'] for r in results )

    avg_scores = calculate_average_scores([result['scores'] for result in results])
    maj     = "PASS" if pass_ct > fail_ct else "FAIL"
    exps    = [r["explanation"] for r in results if r["judgment"] == maj]
    return {"majority_judgment": maj, "majority_explanations": exps, "judge_details": results, "majority_score": avg_scores, "eval_cost": tot_cost}


# ----------------------------------------
# Core benchmarking function
# ----------------------------------------
def benchmark(
        region,
        prompt, task_types, task_criteria, golden_answer,
        max_tokens, model_id,
        in_cost, out_cost,
        temperature, top_p,
        judge_models,
        user_defined_metrics,
        yard_stick=3,
        vision_enabled=False,
        scenario_data=None
):
    logging.debug(f"Starting benchmark for model: {model_id} in region: {region}")
    status                  = "Success"
    time_to_first_byte      = 0
    time_to_last_byte       = 0
    ts                      = get_timestamp()
    perf                    = {}
    err_code                = None
    total_runtime           = 0
    throughput_tps          = 0
    input_tokens            = 0
    output_tokens           = 0
    cost                    = 0
    resp_txt                = ""
    evaluation_cost_data    = 0
    inference_request_count = 0
    params             = {"max_tokens": max_tokens,
                          "temperature": temperature,
                          "top_p": top_p
                          }
    try:
        if "gemini" in model_id:
            params['api_key'] = os.getenv('GOOGLE_API')
        elif 'azure' in model_id:
            params['api_key'] =  os.getenv('AZURE_API_KEY')
        elif 'openai' in model_id:
            params['api_key'] =  os.getenv('OPENAI_API')
        elif "bedrock" in model_id:
            params['aws_region_name'] = region
            model_id = model_id.replace("bedrock", "bedrock/converse")

        # Get image data from scenario if vision is enabled
        image_data = None
        if vision_enabled and scenario_data:
            # Look for image data in scenario - could be any field that's not a standard field
            standard_fields = {"prompt", "task_types", "task_criteria", "golden_answer", "configured_output_tokens_for_request", 
                             "region", "temperature", "user_defined_metrics", "vision_enabled", "model_id", "input_token_cost", 
                             "output_token_cost", "TEMPERATURE", "TOP_P", "inference_profile"}
            for key, value in scenario_data.items():
                if key not in standard_fields and isinstance(value, str) and value.strip():
                    # Assume this is image data if it looks like base64
                    if len(value) > 100 and value.replace('+', '').replace('/', '').replace('=', '').isalnum():
                        image_data = value
                        break
        
        r = run_inference(model_id,
                          prompt,
                          in_cost,
                          out_cost,
                          provider_params=params,
                          stream=True,
                          vision_enabled=vision_enabled,
                          image_data=image_data)

        resp_txt = r['model_response']
        input_tokens = r['input_tokens']
        output_tokens = r['output_tokens']
        total_runtime = r['total_runtime']
        time_to_first_byte = r['time_to_first_byte']
        time_to_last_byte = r['time_to_last_byte']
        throughput_tps = r['throughput_tps']
        cost = r['total_cost']
        inference_request_count = r['retry_count']

        if resp_txt:
            multi = evaluate_with_judges(
                judge_models,
                prompt,
                resp_txt,
                golden_answer,
                task_types,
                task_criteria,
                user_defined_metrics,
                yard_stick=yard_stick
            )
            perf["judge_success"]     = (multi["majority_judgment"] == "PASS")
            perf["judge_explanation"] = ";".join(list(set(multi["majority_explanations"])))
            perf["judge_details"]     = multi["judge_details"]
            perf["judge_scores"]      = multi["majority_score"]
            evaluation_cost_data   = multi["eval_cost"]
        else:
            logging.error(f"Target model error: Model {model_id} returned an empty output.")

    except ClientError as err:
        status = err.response["Error"]["Code"]
        status += f" {str(err)}"
        logging.error(f"API error evaluating {model_id}: {status}")
    except KeyError as key_err:
        status = f"KeyError: {str(key_err)}"
        logging.error(f"Unexpected error evaluating {model_id}: {status}")
    except Exception as e:
        status = str(e)
        logging.error(f"Unexpected error evaluating {model_id}: {status}")

    return {
        "time_to_first_byte":  time_to_first_byte,
        "time_to_last_byte":   time_to_last_byte,
        "total_runtime":       total_runtime,
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
        base_t = s.get("temperature", s.get("TEMPERATURE", cfg["TEMPERATURE"]))
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
def execute_benchmark(scenarios, cfg, unprocessed_dir, yard_stick=3):
    all_recs = []
    unprocessed_records = []
    lock = Lock()
    
    def run_scn(scn):
        recs = []
        local_unprocessed = []
        
        for invocation in range(cfg["invocations_per_scenario"]):
            try:
                logging.info(f"Running scenario: {scn['model_id']}@{scn['region']}, temp={scn['TEMPERATURE']}, invocation {invocation+1}/{cfg['invocations_per_scenario']}")
                # Use per-scenario user_defined_metrics if available, otherwise fall back to global
                scenario_metrics = scn.get("user_defined_metrics", "")
                if scenario_metrics:
                    # Convert comma-separated string to list
                    user_metrics = [m.strip() for m in scenario_metrics.split(",") if m.strip()]
                else:
                    user_metrics = cfg["user_defined_metrics"]
                
                r = benchmark(
                    scn["region"],
                    scn["prompt"],
                    scn["task_types"],
                    scn["task_criteria"],
                    scn["golden_answer"],
                    scn["configured_output_tokens_for_request"],
                    scn["model_id"],
                    scn["input_token_cost"],
                    scn["output_token_cost"],
                    scn["TEMPERATURE"],
                    cfg["TOP_P"],
                    cfg["judge_models"],
                    user_metrics,
                    yard_stick=yard_stick,
                    vision_enabled=scn.get("vision_enabled", False),
                    scenario_data=scn
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
            try:
                result = f.result()
                if result:
                    all_recs.extend(result)
                else:
                    logging.warning("Received empty result from a scenario task")
            except Exception as e:
                logging.error(f"Exception in ThreadPoolExecutor task: {str(e)}", exc_info=True)
                # Record the failure but allow other tasks to continue
                with lock:
                    unprocessed_records.append({
                        "scenario": "Unknown (future failed)",
                        "exception": str(e),
                        "reason": "Exception in ThreadPoolExecutor task",
                        "timestamp": get_timestamp()
                    })
    
    # Write unprocessed records to file if any exist
    if unprocessed_records:
        ts = get_timestamp().replace(':', '-')
        uuid_ = str(uuid.uuid4()).split('-')[-1]
        unprocessed_file = os.path.join(unprocessed_dir, f"unprocessed_{ts}_{uuid_}.json")
        logging.warning(f"Writing {len(unprocessed_records)} unprocessed records to {unprocessed_file}")
        try:
            with open(unprocessed_file, 'w') as f:
                json.dump(unprocessed_records, f, indent=2, default=str)
            logging.info(f"Successfully wrote unprocessed records to {unprocessed_file}")
        except Exception as e:
            logging.error(f"Failed to write unprocessed records file: {str(e)}", exc_info=True)
            
    return all_recs

# ----------------------------------------
# Main entrypoint
# ----------------------------------------
def main(
    input_file,
    output_dir,
    report,
    parallel_calls,
    invocations_per_scenario,
    sleep_between_invocations,
    temp_variants,
    experiment_counts,
    experiment_name,
    user_defined_metrics=None,
    model_file_name=None,
    judge_file_name=None,
    yard_stick=3,
    vision_enabled=False
):
    user_defined_metrics_list = None
    if user_defined_metrics:
        user_defined_metrics_list = [metrics.strip().replace(' ', '-') for metrics in user_defined_metrics.split(',') if metrics != "None"]

    # Get project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Create logs directory with absolute path
    logs_dir = os.path.join(project_root, "logs")
    config_dir = os.path.join(project_root, "default-config")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Setup logging
    ts, log_file = setup_logging(logs_dir, experiment_name)
    logging.info(f"Starting benchmark run: {experiment_name}")
    print(f"Logs are being saved to: {log_file}")

    uuid_ = str(uuid.uuid4()).split('-')[-1]

    # Ensure output directory is absolute
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(project_root, output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create directory for unprocessed records
    unprocessed_dir = os.path.join(output_dir, "unprocessed")
    os.makedirs(unprocessed_dir, exist_ok=True)

    # Use consistent paths for prompt evaluations directory
    eval_dir = os.path.join(project_root, "prompt-evaluations")
    os.makedirs(eval_dir, exist_ok=True)
    
    file_path = os.path.join(eval_dir, input_file)
    judges_list = []

    judge_file_name = judge_file_name if judge_file_name else f"{config_dir}/judge_profiles.jsonl"
    model_file_name = model_file_name if model_file_name else f"{config_dir}/models_profiles.jsonl"
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
        "user_defined_metrics":          user_defined_metrics_list
    }

    # Load scenarios
    raw = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            js = json.loads(line)
            scenario_data = {
                "prompt":                               js.get("text_prompt", ""),
                "task_types":                           js["task"]["task_type"],
                "task_criteria":                        js["task"]["task_criteria"],
                "golden_answer":                        js.get("golden_answer", ""),
                "configured_output_tokens_for_request": js.get("expected_output_tokens", 5000),
                "region":                               js.get("region", "us-east-1"),
                "temperature":                          js.get("temperature", 0.7),
                "user_defined_metrics":                 js.get("user_defined_metrics", ""),
                "vision_enabled":                       vision_enabled,
            }
            
            # Copy all other fields from JSONL (including any image data columns)
            for key, value in js.items():
                if key not in scenario_data and key not in ["text_prompt", "task", "golden_answer", "expected_output_tokens", "region", "temperature", "user_defined_metrics"]:
                    scenario_data[key] = value
            
            raw.append(scenario_data)
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

    for run in range(1, experiment_counts+1):
        logging.info(f"=== Run {run}/{experiment_counts} ===")
        try:
            results = execute_benchmark(scenarios, cfg, unprocessed_dir, yard_stick=int(yard_stick))
            
            if not results:
                logging.error(f"Run {run}/{experiment_counts} produced no results. Check the unprocessed records file.")
                continue
                
            try:
                df = pd.DataFrame(results)
                df["run_count"] = run
                df["timestamp"] = pd.Timestamp.now()
                out_csv = os.path.join(output_dir, f"invocations_{run}_{ts}_{uuid_}_{experiment_name}.csv")
                df.to_csv(out_csv, index=False)
                logging.info(f"Run {run} results saved to {out_csv}")
            except Exception as e:
                logging.error(f"Error saving results for run {run}: {str(e)}", exc_info=True)
        except Exception as e:
            logging.error(f"Critical error in run {run}: {str(e)}", exc_info=True)
            print(f"\nRun {run} failed with error: {str(e)}. Continuing with next run...")

    # Check for unprocessed records
    try:
        unprocessed_files = [f for f in os.listdir(unprocessed_dir) if f.startswith("unprocessed_")]
        if unprocessed_files:
            logging.warning(f"Found {len(unprocessed_files)} files with unprocessed records in {unprocessed_dir}")
            print(f"\nWarning: {len(unprocessed_files)} files with unprocessed records found in {unprocessed_dir}")
    except Exception as e:
        logging.error(f"Error checking for unprocessed records: {str(e)}", exc_info=True)

    if report:
        try:
            from visualize_results import create_html_report
            # Generate report
            report = create_html_report(output_dir, ts)
            print(f"\nBenchmark complete! Report: {report}")
            logging.info(f"Benchmark run complete. Report generated at {report}")
        except ImportError as e:
            logging.error(f"Failed to import visualization module: {str(e)}")
            print("\nBenchmark complete, but report generation failed due to import error.")
        except Exception as e:
            logging.error(f"Error generating report: {str(e)}", exc_info=True)
            print("\nBenchmark complete, but report generation failed.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Advanced Unified LLM Benchmarking Tool")
    p.add_argument("input_file",                  help="JSONL file with scenarios")
    p.add_argument("--output_dir",                default="benchmark-results")
    p.add_argument("--report",                    type=lambda x: x.lower() == 'true', default=True)
    p.add_argument("--parallel_calls",            type=int, default=4)
    p.add_argument("--invocations_per_scenario",  type=int, default=2)
    p.add_argument("--sleep_between_invocations", type=int, default=3)
    p.add_argument("--experiment_counts",         type=int, default=2)
    p.add_argument("--experiment_name",           default=f"Benchmark-{datetime.now().strftime('%Y%m%d')}")
    p.add_argument("--temperature_variations",    type=int, default=0)
    p.add_argument("--user_defined_metrics",      default=None)
    p.add_argument("--model_file_name",           default=None)
    p.add_argument("--judge_file_name",           default=None)
    p.add_argument("--evaluation_pass_threshold", default=3)
    p.add_argument("--vision_enabled",            type=lambda x: x.lower() == 'true', default=False)
    args = p.parse_args()
    main(
        args.input_file,
        args.output_dir,
        args.report,
        args.parallel_calls,
        args.invocations_per_scenario,
        args.sleep_between_invocations,
        args.temperature_variations,
        args.experiment_counts,
        args.experiment_name,
        args.user_defined_metrics,
        args.model_file_name,
        args.judge_file_name,
        args.evaluation_pass_threshold,
        args.vision_enabled
    )