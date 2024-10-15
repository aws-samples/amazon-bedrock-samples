import json
import argparse
import glob


def parse_trace(trace_json):
    trace = json.loads(trace_json)
    total_duration = 0

    for step, step_data in trace.items():
        step_duration = step_data.get('step_duration', 0)
        num_chars = len(step_data['modelInvocationInput'].get('text', ""))
        total_duration += step_duration
        print(f"\n{step}: {step_duration:.3f} seconds, {num_chars} chars")

        # Orchestration
        if "modelInvocationInput" in step_data:
            print("  Orchestration:")
            print(f"    Type: {step_data['modelInvocationInput'].get('type', 'N/A')}")
            print(f"    Trace ID: {step_data['modelInvocationInput'].get('traceId', 'N/A')}")

        # Rationale
        if "rationale" in step_data:
            text = step_data['rationale'].get('text', 'N/A')
            num_chars = len(text)
            print(f"  Rationale: {num_chars} chars")
            print(f"    {text}")

        # Invocation
        if "invocationInput" in step_data:
            print("  Invocation:")
            invocation = step_data['invocationInput'].get('actionGroupInvocationInput', {})
            print(f"    Action Group: {invocation.get('actionGroupName', 'N/A')}")
            print(f"    Function: {invocation.get('function', 'N/A')}")
            print("    Parameters:")
            for param in invocation.get('parameters', []):
                print(f"      {param.get('name', 'N/A')}: {param.get('value', 'N/A')}")

        # Observation
        if "observation" in step_data:
            obs = step_data['observation']
            if 'actionGroupInvocationOutput' in obs:
                text = obs['actionGroupInvocationOutput'].get('text', 'N/A')
            elif 'finalResponse' in obs:
                text = obs['finalResponse'].get('text', 'N/A')
            num_chars = len(text)
            print(f"  Observation: {num_chars} chars")
            print(f"    Type: {obs.get('type', 'N/A')}")
            if 'actionGroupInvocationOutput' in obs:
                print(f"    Output: {text}")
            elif 'finalResponse' in obs:
                print(f"    Final Response: {text}")
    print(f"\nTotal Duration: {total_duration:.2f} seconds")


def process_file(filename):
    print(f"\nProcessing file: {filename}")
    with open(filename, 'r') as file:
        trace_json = file.read()
    parse_trace(trace_json)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="The file(s) to process. Wildcards are supported.")
    args = parser.parse_args()

    for file_pattern in args.files:
        # Expand wildcards and get list of matching files
        matching_files = glob.glob(file_pattern)

        if not matching_files:
            print(f"No files found matching pattern: {file_pattern}")
            continue

        for filename in matching_files:
            if 'xlsx' in filename.lower():
                continue
            process_file(filename)


if __name__ == "__main__":
    main()