import boto3
import time
from datetime import datetime
import uuid
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import argparse
from pathlib import Path
import json
import pandas as pd
import os

global bedrock_agent_runtime_client


def process_response(query, session_state, trial_id, query_id, resp, show_code_use: bool = False):

    """
    Function that parsers the invoke_model response of an agent
    
    Args:
        query (str): user query
        session_state (dict): session state used in invoke model
        trial_id (int): trial id for user query
        query_id (int): query id inside a conversation
        resp (dict): the JSON response of the invokeModel API
        show_code_use (bool): if the code usage should be displayed as markdown
    """
    trace_for_response = ""
    #print(f"\n## Trial {trial_id} - Query {query_id}")
    trace_for_response += f"\n## Trial {trial_id} - Query {query_id}"
    #print(f"\n### User Query\n{query}")
    trace_for_response += f"\n### User Query\n{query}"
    #print(f"\n### Session State\n{session_state}")
    trace_for_response += f"\n### Session State\n{session_state}"
    if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
        #print(f"API Response was not 200: {resp}")
        trace_for_response += f"API Response was not 200: {resp}"
    start_time = time.time()

    event_stream = resp['completion']
    #print('before event stream')
    for event in event_stream:
        #print(event)
        if 'files' in event.keys():
            files_event = event['files']
            #print("\n### Files")
            files_list = files_event['files']
            trace_for_response += f"\n### Files"
            for this_file in files_list:
                trace_for_response += f"{this_file['name']} \({this_file['type']}\)"
                file_bytes = this_file['bytes']

                # save bytes to file, given the name of file and the bytes
                file_name_temp = f"{trial_id}_{query_id}_" + this_file['name']
                file_name = os.path.join('output', file_name_temp)
                with open(file_name, 'wb') as f:
                    f.write(file_bytes)
                #if this_file['type'] == 'image/png' or this_file['type'] == 'image/jpeg':
                #    img = mpimg.imread(file_name)
                #    plt.imshow(img)
                #    plt.show()
                
                trace_for_response += f"Saved {file_name} as output"
        #print('before trace')
        if 'trace' in event.keys():
            trace_object = event.get('trace')['trace']
            #print('before guardrail trace')
            if "guardrailTrace" in trace_object:
                #print("entering trace")
                guardrail_trace = trace_object['guardrailTrace']
                #print(guardrail_trace)
                
                guardrail_action = guardrail_trace['action']
                #print(f"\n### Guardrails\nAction: {guardrail_action}")
                trace_for_response += f"\n### Guardrails\nAction: {guardrail_action}"
                if guardrail_action == "INTERVENED":
                    input_assessments = guardrail_trace['inputAssessments']
                    #print(f"\n#### input Assessments: {input_assessments}")
                    trace_for_response += f"\n#### input Assessments: {input_assessments}"
                    end_time = time.time()
                    execution_time = (end_time - start_time)
                    return input_assessments, trace_for_response, execution_time
            elif "orchestrationTrace" in trace_object:
                #print('in orchestrationTrace')
                trace_event = trace_object['orchestrationTrace']

                if 'modelInvocationInput' in trace_event.keys():
                    pass

                if 'rationale' in trace_event.keys():
                    rationale = trace_event['rationale']['text']
                    #print(f"\n### Rationale\n{rationale}")
                    trace_for_response +=f"\n### Rationale\n{rationale}"

                if 'invocationInput' in trace_event.keys():
                    #print(f'in invocationInput{trace_event}')
                    inv_input = trace_event['invocationInput']
                    parameters = []
                    if 'codeInterpreterInvocationInput' in inv_input:
                        gen_code = inv_input['codeInterpreterInvocationInput']['code']
                        code = f"```python\n{gen_code}\n```"
                        #print(f"\n### Generated code\n{code}")
                        trace_for_response += f"\n### Generated code\n{code}"
                    if "actionGroupInvocationInput" in inv_input:
                        action_group_name = inv_input["actionGroupInvocationInput"]["actionGroupName"]
                        execution_type = inv_input["actionGroupInvocationInput"]["executionType"]
                        
                        #print("\n### Action group invocation call")
                        trace_for_response += "\n### Action group invocation call"
                        #print(f"\nExecution Type {execution_type}")
                        trace_for_response += f"\nExecution Type {execution_type}"
                        if "parameters" in inv_input["actionGroupInvocationInput"]:
                            parameters = inv_input["actionGroupInvocationInput"]["parameters"]
                        if "requestBody" in inv_input["actionGroupInvocationInput"]:
                            try:
                                parameters = inv_input["actionGroupInvocationInput"]['requestBody']['content']['application/json']
                            except:
                                parameters = []
                            
                        if "function" in inv_input["actionGroupInvocationInput"]:
                            execution_function = inv_input["actionGroupInvocationInput"]["function"]
                            # print(f"\nInvoking action group {action_group_name} function {execution_function}")
                            trace_for_response += f"\nInvoking action group {action_group_name} function {execution_function}"
                        if "apiPath" in inv_input["actionGroupInvocationInput"]:
                            execution_function = inv_input["actionGroupInvocationInput"]["apiPath"]
                            # print(f"\nInvoking action group {action_group_name} function {execution_function}")
                            trace_for_response += f"\nInvoking action group {action_group_name} function {execution_function}"
                        if len(parameters) > 0:
                            #print(f"\n#### Parameters")
                            trace_for_response += f"\n#### Parameters"
                        for parameter in parameters:
                            param_name = parameter["name"]
                            param_type = parameter["type"]
                            param_val = parameter["value"]
                            #print(f"\nName: {param_name}, Type: {param_type}, Value: {param_val}")
                            trace_for_response += f"\nName: {param_name}, Type: {param_type}, Value: {param_val}"
                    if "knowledgeBaseLookupInput" in inv_input:
                        kb_id = inv_input["knowledgeBaseLookupInput"]["knowledgeBaseId"]
                        kb_query = inv_input["knowledgeBaseLookupInput"]["text"]
                        #print("\n### Knowledge Base invocation call")
                        trace_for_response += f"\n### Knowledge Base invocation call"
                        #print(f"\nInvoking knowledge base {kb_id} with query {kb_query}")
                        trace_for_response += f"\nInvoking knowledge base {kb_id} with query {kb_query}"

                if 'observation' in trace_event.keys():
                    obs = trace_event['observation']
                    if "knowledgeBaseLookupOutput" in obs:
                        retrieve_references = obs["knowledgeBaseLookupOutput"]["retrievedReferences"]
                        #print(f"\n### Knowledge Base references")
                        trace_for_response += f"\n### Knowledge Base references"
                        for kb_ref in retrieve_references:
                            content = kb_ref["content"]["text"]
                            ref_location = kb_ref["location"]["s3Location"]["uri"]
                            #print(f"\nContent: {content}")
                            #print(f"\nContent URI: {ref_location}")
                            trace_for_response += f"\n#### Content\n{content}"
                            trace_for_response += f"\n#### Content URI\n{ref_location}"
                    if "actionGroupInvocationOutput" in obs:
                        action_group_response = obs["actionGroupInvocationOutput"]["text"]
                        #print(f"\n### Action Group response\n{action_group_response}")
                        trace_for_response += f"\n### Action Group Response\n{action_group_response}"
                    if 'codeInterpreterInvocationOutput' in obs:
                        if 'executionOutput' in obs['codeInterpreterInvocationOutput'].keys() and show_code_use:
                            raw_output = obs['codeInterpreterInvocationOutput']['executionOutput']
                            output = f"```\n{raw_output}\n```"
                            #print(f"\n### Output from code execution\n{output}")
                            trace_for_response +=f"\n### Output from code execution\n{output}"

                        if 'executionError' in obs['codeInterpreterInvocationOutput'].keys():
                            #print(f"\n### Error from code execution\n{obs['codeInterpreterInvocationOutput']['executionError']}")
                            trace_for_response +=f"\n### Error from code execution\n{obs['codeInterpreterInvocationOutput']['executionError']}"

                        if 'files' in obs['codeInterpreterInvocationOutput'].keys():
                            #print("\n### Files generated\n")
                            trace_for_response +=f"\n### Files generated\n"
                            #print(f"{obs['codeInterpreterInvocationOutput']['files']}")
                            trace_for_response +=f"{obs['codeInterpreterInvocationOutput']['files']}"

                    if 'finalResponse' in obs:
                        final_resp = obs['finalResponse']['text']
                        #print(f"\n### Final response\n{final_resp}")
                        trace_for_response +=f"\n### Final response\n{final_resp}"

                        end_time = time.time()
                        execution_time = (end_time - start_time)
                        return final_resp, trace_for_response, execution_time
            else:
                print(trace_object)

def add_file_to_session_state(local_file_name=None, file_url=None, use_case='CODE_INTERPRETER', session_state=None):
    """
    Function that populates the sessionState parameter for an Agent invocation call with files that can be used
    for CHAT with the file or for CODE_INTERPRETER capabilities inside of the agent
    
    Args:
        local_file_name (str): the name of the file to path. Either file_name or file_url should be not None
        file_url (str): the s3 url for the file to be used. Either file_name or file_url should be not None
        use_case (str): one of CHAT or CODE_INTERPRETER
        session_state (dict): the current session state
    """
    if use_case != "CHAT" and use_case != "CODE_INTERPRETER":
        raise ValueError("Use case must be either 'CHAT' or 'CODE_INTERPRETER'")
    if not session_state:
        session_state = {
            "files": []
        }
    if (local_file_name is None) and (file_url is None):
        raise ValueError("Either local_file_name or file_url should be not None")
    if local_file_name and not file_url:
        file_name = local_file_name
    elif file_url and not local_file_name:
        file_name = file_url
    else:
        raise ValueError("You should only provide local_file_name OR file_url")
    type = file_name.split(".")[-1].upper()
    name = file_name.split("/")[-1]

    if type == "CSV":
        media_type = "text/csv" 
    elif type in ["XLS", "XLSX"]:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "text/plain"
    if local_file_name:
        named_file = {
            "name": name,
            "source": {
                "sourceType": "BYTE_CONTENT", 
                "byteContent": {
                    "mediaType": media_type,
                    "data": open(local_file_name, "rb").read()
                }
            },
            "useCase": use_case
        }
        session_state['files'].append(named_file)
    elif file_url:
        path_file = {
            "name": name,
            "source": {
                "sourceType": "S3", 
                's3Location': {
                        'uri': file_url
                },
            },
            "useCase": use_case
        }
        session_state['files'].append(path_file)

    return session_state


def invoke_agent_helper(
    query, trial_id, query_id, session_id, agent_id, alias_id, session_state=None, end_session=False, show_code_use=False
):
    """
    Support function to invoke agent
    
    Args:
        query (str): user query
        trial_id (int): trial id for user query
        query_id (int): query id inside a conversation
        session_id (str): id for the session
        agent_id (str): id for the agent
        alias_id (str): id of the agent alias
        session_state (dict): a session id to use to maintain the session context
        end_session (bool): if the session should be terminated
        show_code_use (bool): if we should show code
    """
    
    if not session_state:
        session_state = {}
    
    # invoke the agent API
    agent_response = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        enableTrace=True, # Force tracing on if showing code use
        endSession=end_session,
        sessionState=session_state
    )
    return process_response(query, session_state, trial_id, query_id, agent_response, show_code_use=show_code_use)


def test_query(
    queries_list, agent_id, alias_id, number_trials,
    session_state=None, show_code_use=False, file_prefix=""
):
    #print('parms for test_query',queries_list, agent_id, alias_id, number_trials,session_state)
    """
    Support function to test invoke agent for latency and responses
    
    Args:
        queries_list (list): user query
        agent_id (str): id for the agent
        alias_id (str): id of the agent alias
        number_trials (int): number of trials per query
        session_state (dict): a session id to use to maintain the session context
        show_code_use (bool): if we should show code
        file_prefix (str): prefix to add to output files
    """
    latency_data = []
    folder_prefix = "conversation"
    
    if file_prefix != "":
        folder_prefix = file_prefix
        file_prefix += "_"
    Path("output/").mkdir(parents=True, exist_ok=True)
    
    now = datetime.now() # current date and time
    date_time = now.strftime("%Y_%m_%d_%H_%M_%S")
    Path(f"output/{folder_prefix}/").mkdir(parents=True, exist_ok=True)
    for i in range(number_trials):
        print(f"================== trial {i} ==================")
        session_id:str = str(uuid.uuid1())
        j = 0
        for query in queries_list:
            if type(query) == dict:
                if "file" in query:
                    local_file_name = None
                    file_url = None
                    if "s3" in query["file"]:
                        file_url = query["file"]
                    else:
                        local_file_name = query["file"]
                    use_case = query["type"]
                    session_state = add_file_to_session_state(
                        local_file_name=local_file_name,
                        file_url=file_url,
                        use_case=use_case,
                        session_state=None
                    )
                if "promptSessionAttributes" in query:
                    if session_state is None:
                        session_state = {}
                    session_state["promptSessionAttributes"] = query["promptSessionAttributes"]
                if "sessionAttributes" in query:
                    if session_state is None:
                        session_state = {}
                    session_state["sessionAttributes"] = query["sessionAttributes"]
                if "query" in query:
                    query = query["query"]
            print(f"Query: {query}")
            #print('before invoke_agent',query, i, j, session_id, agent_id, alias_id)
            final_resp, trace_for_response, execution_time = invoke_agent_helper(
                query, i, j, session_id, agent_id, alias_id,
                session_state=session_state,
                end_session=False, show_code_use=show_code_use
            )
            print(f"Final response: {final_resp}")
            print(f"Execution time: {execution_time}")
            trace_file = f'output/{folder_prefix}/{file_prefix}test_{i}_query_{j}_{date_time}.md'
            with open(trace_file, 'w') as output:
                output.write(trace_for_response)
            latency_data.append({
                "execution": (i+1),
                "query": query,
                "query_order": (j+1),
                "execution_time": execution_time,
                "final_response": final_resp,
                "trace_file": trace_file
            })
            j += 1
        invoke_agent_helper(
            "end", i, -1, session_id, agent_id, alias_id,
            session_state=session_state, 
            end_session=True, show_code_use=show_code_use
        )
    latency_df = pd.DataFrame(latency_data)
    latency_df.to_excel(f"output/{folder_prefix}/{file_prefix}latency_summary_{date_time}.xlsx", index=False)
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='agent_tester',
        description='Test agents for Amazon Bedrock for latency and store the traces'
    )
    parser.add_argument('--test_file', type=str)
    parser.add_argument('--agent_id', type=str)
    parser.add_argument('--agent_alias_id', type=str, default="TSTALIASID")
    parser.add_argument('--region', type=str, default="us-east-1")
    parser.add_argument('--number_trials', type=int, default=5)
    parser.add_argument('--memory_id', type=str, default=None)
    parser.add_argument('--show_code_use', type=bool, default=True)
    args = parser.parse_args()
    print(args)
    bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=args.region)
    if args.test_file.endswith(".json"):
        f = open(args.test_file)
        test_cases = json.load(f)
        for key in test_cases:
            #print('key',key)

            queries = test_cases[key]
            #print(f'queries{queries}')
            test_query(
                queries, args.agent_id, args.agent_alias_id,
                args.number_trials, None, args.show_code_use,
                key
            )
    else:
        raise ValueError("please provide a JSON input file with your test data")