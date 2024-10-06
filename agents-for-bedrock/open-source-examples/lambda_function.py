

import json

def run_python_code(python_string):
    # Python code must contain "result" variable
    
    try:
        if "result" in python_string:
            
            print("Running the following python string")
            print(python_string)
            exec(python_string, globals())
            
            return result 
        else:
            return "Error: you must include the variable 'result' in the code you submit"
    except Exception as e:
        return e
        

def lambda_handler(event, context):

    print(event)
    
    ## Langchain wraps request and response in 'body', but Bedrock agents does not
    if 'body' in event:
        event = json.loads(event['body'])
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody =  {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }


    
    if function == 'run_python_code':
        
        
        cmd = "print('no valid python string entered')"
        for param in parameters:
            if param["name"] == "python_string":
                python_string = param["value"]

        output = run_python_code(python_string)
        responseBody =  {
            'TEXT': {
                "body": f"output: {output}"
            }
        }
    else:
        responseBody =  {
            'TEXT': {
                "body": f"output: Function called is invalid: {function}"
            }
        }
        
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }
    
    ## Langchain wraps request and response in 'body', but Bedrock agents does not
    
    if isinstance( event['agent'] , dict):
        function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    else:
        function_response = {'body': {'response': action_response, 'messageVersion': event['messageVersion']}}
        
    
    print("Response: {}".format(function_response))

    return function_response
