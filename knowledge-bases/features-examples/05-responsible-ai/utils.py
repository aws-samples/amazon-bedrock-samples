import re
import json

def print_results(kb_response, response):
    # Print the KB retrieval results
    print("Knowledge Base retrieval results:\n")
    for i, result in enumerate(kb_response['retrievalResults'], start=1):
        text = result['content']['text']
        text = re.sub(r'\s+', ' ', text)
        print(f"Chunk {i}:\n{text}\n")
    
    # Print the text
    print(f"MODEL RESPONSE:\n")
    print(response['output']['message']['content'][0]['text'])

def print_results_with_guardrail(kb_response, response):
    # Print the KB retrieval results
    print("Knowledge Base retrieval results:\n")
    for i, result in enumerate(kb_response['retrievalResults'], start=1):
        text = result['content']['text']
        text = re.sub(r'\s+', ' ', text)
        print(f"Chunk {i}:\n{text}\n")
    
    # Print the text
    print(f"MODEL RESPONSE:\n")
    print(response['output']['message']['content'][0]['text'])
    
    # Print the outputAssessments scores
    print("\nCONTEXTUAL GROUNDING SCORES:\n")
    for key, assessments in response['trace']['guardrail']['outputAssessments'].items():
        for assessment in assessments:
            for filter in assessment['contextualGroundingPolicy']['filters']:
                print(f"Filter type: {filter['type']}, Score: {filter['score']}, Threshold: {filter['threshold']}, Passed: {filter['score'] >= filter['threshold']}")
    
    if response['stopReason'] == 'guardrail_intervened':
        print("\nGuardrail intervened")
        print("Model final response ->", response['output']['message']['content'][0]['text'])
        print("Model response ->", json.dumps(json.loads(response['trace']['guardrail']['modelOutput'][0]), indent=2))