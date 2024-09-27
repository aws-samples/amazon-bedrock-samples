import boto3
import time
from datetime import datetime
import uuid
import argparse
from pathlib import Path
import json
import pandas as pd
from llm_judge import eval_all  

global bedrock_agent_runtime_client


def process_response(query, session_state, trial_id, query_id, resp):
    """
    Function that parsers the invoke_model response of an agent

    Args:
        query (str): user query
        session_state (dict): session state used in invoke model
        trial_id (int): trial id for user query
        query_id (int): query id inside a conversation
        resp (dict): the JSON response of the invokeModel API
    """
    start_time = time.time()
    step_time = start_time
    json_trace = {}
    #Check for Error
    if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
        json_trace["Error"] = f"API Response was not 200: {resp}"
    event_stream = resp['completion']
    step = 0
    for event in event_stream:
        
        # If trace in response, print trace
        if "trace" in event.keys():
            trace_object = event.get('trace')['trace']
            if "orchestrationTrace" in trace_object:
                trace_event = trace_object['orchestrationTrace']
                if "modelInvocationInput" in trace_event: # the input for the pre-processing step, print each of these steps
                    if step > 0:
                        step_duration = (time.time() - step_time)
                        step_time = time.time()
                        json_trace[f"Step_{step}"]["step_duration"] = step_duration
                    print(f"Step {step}")
                    step += 1
                    if "Step_{step}" not in json_trace: # if current step isn't in the json_trace dictionary, add it
                        json_trace[f"Step_{step}"] = {}
                    json_trace[f"Step_{step}"]["modelInvocationInput"] = trace_event["modelInvocationInput"]
                elif "rationale" in trace_event: # the reasoning used to justify an action 
                    json_trace[f"Step_{step}"]["rationale"] = trace_event["rationale"]
                elif "SDK_UNKNOWN_MEMBER" in trace_event:
                    json_trace[f"Step_{step}"]["SDK_UNKNOWN_MEMBER"] = trace_event["SDK_UNKNOWN_MEMBER"]
                elif 'invocationInput' in trace_event: # the action or knowledge base being invoked
                    if f"Step_{step}" not in json_trace:
                        step += 1
                        json_trace[f"Step_{step}"] = {}

                    json_trace[f"Step_{step}"]["invocationInput"] = trace_event["invocationInput"]
                elif "observation" in trace_event: #result of an action
                    json_trace[f"Step_{step}"]["observation"] = trace_event["observation"]
                    obs = trace_event['observation']
                    if 'finalResponse' in obs: # the response back to user
                        step_duration = (time.time() - step_time)
                        json_trace[f"Step_{step}"]["step_duration"] = step_duration

        if 'chunk' in event: # get citations for response
            data = event['chunk']['bytes']
            agent_answer = data.decode('utf8')
            execution_time = (time.time() - start_time)
            citations = event.get('chunk', {}).get('attribution', {}).get('citations', [])
            fully_cited_answer = ""
            if citations:
                curr_citation_idx = 0
                for citation in citations:
                    start = citation['generatedResponsePart']['textResponsePart']['span']['start'] - (
                                curr_citation_idx + 1)  # +1
                    end = citation['generatedResponsePart']['textResponsePart']['span']['end'] - (
                                curr_citation_idx + 2) + 4  # +2
                    if len(citation['retrievedReferences']) > 0:
                        ref_url = citation['retrievedReferences'][0]['location']['s3Location']['uri']
                    else:
                        ref_url = "missing_reference"

                    fully_cited_answer += agent_answer[start:end] + " [" + ref_url + "] "

                    if curr_citation_idx == 0:
                        answer_prefix = agent_answer[:start]
                        fully_cited_answer = answer_prefix + fully_cited_answer

                    curr_citation_idx += 1
                json_trace[f"Step_{step}"]["citations"] = citations
            if f"Step_{step}" not in json_trace:
                json_trace[f"Step_{step}"] = {}
            json_trace[f"Step_{step}"]["original_agent_answer"] = agent_answer
            json_trace[f"Step_{step}"]["fully_cited_answer"] = fully_cited_answer
            if fully_cited_answer != "":
                # finally, replace the original answer w/ the fully cited answer
                agent_answer = fully_cited_answer
            return agent_answer, execution_time, json_trace, None
        if 'returnControl' in event:
            if step > 0:
                step_duration = (time.time() - step_time)
                step_time = time.time()
                json_trace[f"Step_{step}"]["step_duration"] = step_duration
            if 'invocationInputs' in event['returnControl']:
                json_trace[f"Step_{step}"]["invocationInputs"] = event['returnControl']['invocationInputs']
            if 'invocationId' in event['returnControl']:
                json_trace[f"Step_{step}"]["invocationId"] = event['returnControl']['invocationId']
            agent_answer = event['returnControl']
            execution_time = (time.time() - start_time)
            return agent_answer, execution_time, json_trace, event['returnControl']['invocationId']


def add_file_to_session_state(local_file_name=None, file_url=None, use_case='CODE_INTERPRETER', session_state=None):
    """
    Function that populates the sessionState parameter for an Agent invocation call with files that can be used
    for CHAT with the file or for CODE_INTERPRETER capabilities inside-of the agent
    
    Args:
        local_file_name (str): the name of the file to path. Either file_name or file_url should be not None
        file_url (str): the s3 url for the file to be used. Either file_name or file_url should be not None
        use_case (str): one of CHAT or CODE_INTERPRETER
        session_state (dict): the current session state
    """
    # Error handling
    if use_case != "CHAT" and use_case != "CODE_INTERPRETER":
        raise ValueError("Use case must be either 'CHAT' or 'CODE_INTERPRETER'")
    if not session_state:
        session_state = {
            "files": []
        }
    # identify file type and save as needed
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
    query, trial_id, query_id, session_id, agent_id, alias_id, memory_id, session_state=None, end_session=False
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
        memoryId=memory_id,
        endSession=end_session,
        sessionState=session_state
    )
    return process_response(query, session_state, trial_id, query_id, agent_response)


def test_query(
    show_code_use, queries_list, agent_id, alias_id, number_trials, memory_id, session_id, 
    session_state=None, file_prefix="", sleep_time=0, 
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
        file_prefix (str): prefix to add to output files
        sleep_time (int): seconds to sleep between invocations
        memory_id (str): memory id for the agent for a previous conversation
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
    # repeat trial for as many time as specified by number_trials
    for i in range(number_trials):
        print(f"================== trial {i} ==================")
        if session_id == 'None':
            session_id:str = str(uuid.uuid1())
        j = 0
        invocation_id = None
        for query in queries_list:
            session_state = None
            if type(query) == dict:
                if "file" in query:
                    local_file_name = None
                    file_url = None
                    if "s3" in query["file"]:
                        file_url = query["file"]
                    else:
                        local_file_name = query["file"]
                    print(local_file_name, file_url)
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
                if "returnControlInvocationResults" in query:
                    if session_state is None:
                        session_state = {}
                    session_state['returnControlInvocationResults'] = query['returnControlInvocationResults']
                    session_state['invocationId'] = invocation_id
                    query = ""
                if "query" in query:
                    query = query["query"]
            print(f"Query: {query}, Invocation Id: {invocation_id}, session state: {session_state}")
            final_resp, execution_time, json_trace, invocation_id = invoke_agent_helper(
                query, i, j, session_id, agent_id, alias_id, memory_id,
                session_state=session_state, end_session=False
            )

            print(f"Final response: {final_resp}")
            print(f"Execution time: {execution_time}")
            trace_file_json = f'output/{folder_prefix}/{file_prefix}test_{i}_query_{j}_{date_time}.json'
            with open(trace_file_json, 'w') as output:
                json.dump(json_trace, output)
            latency_data.append({
                "agent_id": agent_id,
                "execution": (i+1),
                "query_order": (j+1),
                "trace_file": trace_file_json,
                "execution_time": execution_time,
                "query": query,
                "session_state": str(session_state),
                "final_response": final_resp,
                "number_steps": len(json_trace.keys())
            })
            j += 1
            if sleep_time > 0:
                time.sleep(sleep_time)
        invoke_agent_helper(
            "end", i, -1, session_id, agent_id, alias_id, memory_id,
            session_state=session_state, 
            end_session=True
        )
    latency_df = pd.DataFrame(latency_data)
    latency_df.to_excel(f"output/{folder_prefix}/{file_prefix}latency_summary_{date_time}.xlsx", index=False)
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='agent_tester',
        description='Test agents for Amazon Bedrock for latency and store the traces'
    )
    parser.add_argument('--test_file', type=str) # json input file containing test data
    parser.add_argument('--agent_id', type=str) #ID for the agent
    parser.add_argument('--agent_alias_id', type=str, default="TSTALIASID") #ID for agent alias
    parser.add_argument('--region', type=str, default="us-east-1") #region
    parser.add_argument('--number_trials', type=int, default=5) # number of trials per query
    parser.add_argument('--sleep_time', type=int, default=0) # how long to wait before running next query
    parser.add_argument('--show_code_use', type=bool, default=True) #Boolean for whether to show code or not
    parser.add_argument('--memory_id', type=str, default='None') # Memory ID 
    parser.add_argument('--session_id', type=str, default='None') # Session ID to continue a previous conversation
    parser.add_argument('--output', type=str, default="./output") #path to the folder that hold all the agent trial outputs

    args = parser.parse_args()
    print(args)
    bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=args.region)

    if args.test_file.endswith(".json"):
        f = open(args.test_file)
        test_cases = json.load(f)
        for key in test_cases:
            queries = test_cases[key]
            test_query(
                args.show_code_use, queries, args.agent_id, args.agent_alias_id,
                args.number_trials, args.memory_id, args.session_id, None,
                key, 60
            )
        eval_all(Path(f"output"))
    else:
        raise ValueError("please provide a JSON input file with your test data")
