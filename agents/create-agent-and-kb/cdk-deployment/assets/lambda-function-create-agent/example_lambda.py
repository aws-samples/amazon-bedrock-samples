import json 

def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def get_named_property(event, name):
    return next(item for item in event['requestBody']['content']['application/json']['properties'] if item['name'] == name)['value']
    
def doSomethingUsingProperties(event):
    int_property_value1 = int(get_named_property(event, 'property_name1'))
    float_property_value2 = float(get_named_property(event, 'property_name2'))
    string_property_value3 = get_named_property(event, 'property_name3')

   # TODO: implement

    return {
      "attribute1": "some value",
      "attribute2": "some other value"
    }
 
def doSomethingUsingParameters(event):
   my_input_parameter = get_named_value(event['parameters'], 'my_parameter_name')

   # TODO: implement

   return {
      "attribute1": "some value",
      "attribute2": "some other value"
    }

def lambda_handler(event, context):
    print(event)
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']
    
    if api_path == '/doSomethingUsingParameters':
        result = doSomethingUsingParameters(event) 
    elif api_path == '/doSomethingUsingProperties':
        result = doSomethingUsingProperties(event)
    else:
        response_code = 404
        result = f"Unrecognized api path: {action_group}::{api_path}"
        
        response_body = {
            'application/json': {
                'body': result
            }
        }
            
        action_response = {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'], # never HTTPMethod, always httpMethod
            'httpStatusCode': response_code,
            'responseBody': response_body
        }
    
        api_response = {'messageVersion': '1.0', 'response': action_response}
        return api_response