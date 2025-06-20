import logging
import os
import io
import csv
from time import sleep

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine, text
from datetime import datetime

from prompts import ( DEFAULT_SYSTEM_PROMPT,
                     CURRENT_PLAN_PROMPT_TEMPLATE,
                     END_TURN_PROMPT,
                     TOOL_GROUP_PROMPT_TEMPLATE
                    )

from utils import extract_xml_content


class BaseAgent():
    
    def __init__(self, model_id, 
                 memory_table_name, 
                 system_prompt_template=DEFAULT_SYSTEM_PROMPT,
                 requests_per_minute_limit=None):
        
        self.model_id = model_id
        
        # Tooling
        self.tool_spec_list = []
        
        # System Prompt
        self.system_prompt_template = system_prompt_template
        self.system_current_plan = None
        
        # Initialize clients and resources
        self.bedrock = boto3.client("bedrock-runtime")
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(memory_table_name)
        
        # Used for timing
        self.start_time = None
        self.requests_per_minute_limit=requests_per_minute_limit
        

            
    def invoke_agent(self, input_text, 
                     temperature=0.5, 
                     max_tokens=4096, max_retries=3):
    
        # Initialize message list
        # TODO implement session history retrieval
        messages = []
        
        # Get the timestamp chunk to append to the message 
        # Making the agent run time aware
        self.start_time = datetime.now()
        timestamp_chunk = self.create_timestamp_content_block(start_time=self.start_time)        
                
        initial_user_message = {
            "role": "user",
            "content": [
                {
                    "text": input_text
                },
                timestamp_chunk
            ]
        }
        
        messages.append(initial_user_message)
        
        print(f"User: {input_text}")
        print("Beginning execution loop")
        
        # Begin main loop
        
        while True:
            
            # Limit how fast the agent executes
            if self.requests_per_minute_limit:
                sleep(60/self.requests_per_minute_limit)
            
            
            #Inject current execution plan into system prompt
            system_prompt = self.system_prompt_template.format(
                current_plan_prompt=CURRENT_PLAN_PROMPT_TEMPLATE.format(current_plan=self.system_current_plan)
            )
            
            #Invoke the Converse API
            
            current_retry_count = 0
            
            while current_retry_count < max_retries:
                try:
                    print("Invoking converse API")
                    response = self.bedrock.converse(
                        modelId=self.model_id,
                        messages=messages,
                        toolConfig=self.get_tool_config(),
                        system=[{"text": system_prompt}],
                        inferenceConfig={
                            "maxTokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    
                    break
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    error_message = e.response["Error"]["Message"]
                    
                    print(f"Encountered error: {e}")
                    

                    if current_retry_count >= max_retries:
                        print(f"Exceeded max retry. Encountered error: {e}")
                        raise(e)
                    else:
                        print(f"Retrying. Encountered error: {e}")
                        
                        if error_code == "ThrottlingException":
                            # Reduce RPM limit by 10%
                            self.requests_per_minute_limit = self.requests_per_minute_limit * 0.9
                            print(f"ThrottlingException. Reducing RPM limit. New Value: {self.requests_per_minute_limit}")
                            sleep(60/self.requests_per_minute_limit)
                        
                        current_retry_count +=1 
                    
            
            #Append the AI message to the memory list
            messages.append(response["output"]["message"])
            
            # Extract plan
            for chunk in response["output"]["message"]["content"]:
                if "text" in chunk:
                    current_plan = extract_xml_content(chunk["text"], "current_plan")
                    if current_plan:
                        self.system_current_plan = current_plan
            
            # Handle stopReasons
            if response["stopReason"] == "tool_use":
                tool_result_message = self.handle_tool_use(message=response["output"]["message"])
                messages.append(tool_result_message)
            elif response["stopReason"] == "end_turn":
                if len(messages[-1]['content']) == 0:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "text": END_TURN_PROMPT
                            }
                        ]
                    })
                else:
                    final_response = extract_xml_content(messages[-1]['content'][0]['text'], "final_response")
                    if final_response:
                        
                        # Reset the system prompt
                        self.system_prompt_template = DEFAULT_SYSTEM_PROMPT
                        self.system_current_plan = None
                        
                        return final_response
                    else:
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "text": END_TURN_PROMPT
                                }
                            ]
                        })
                
                
    def create_timestamp_content_block(self, start_time, current_time=None):
        "Returns a timestamp content block"
        
        if current_time is None:
            current_time = datetime.now()
        
        total_runtime = current_time-start_time
        
        return {
            "text": f"Current Datetime: {datetime.now()}\nTotal Runtime: {total_runtime}"
        }
        
    def add_tool(self, tool_spec, function):
        """
        Adds a tool to the tool config and monkey patch to the class
        
        Parameters:
        - tool_spec (dict) A Converse API tool spec
        - function (Callable) A function that can be called
        """
        
        # Add the tool specification to the list
        self.tool_spec_list.append(tool_spec)
        
        # Get the name of the function from the tool_spec
        function_name = tool_spec.get('toolSpec', {}).get('name')
        
        if function_name:
            # Monkey patch the function to the class
            setattr(self.__class__, function_name, function)
        else:
            raise ValueError("Tool specification must include a 'name' field")
        
        
    def add_tool_group(self, tool_group):
        """
        Adds a tool group to the agent
        
        Parameters:
        - tool_group (List[dict]) A list of dictionaries containing tool_spec and function
        """
                
        tools_prompt = ""
        
        
        for tool in tool_group["tools"]:
            tools_prompt += (f"- {tool['tool_spec']['toolSpec']['name']}\n")
            self.add_tool(tool["tool_spec"], tool["function"])
        
        tool_group_prompt = TOOL_GROUP_PROMPT_TEMPLATE.format(
            tool_group_name=tool_group["tool_group_name"],
            tool_group_instructions=tool_group["usage_instructions"],
            tools=tools_prompt,
        )
        
        self.system_prompt_template += (tool_group_prompt)
    
    def get_tools(self):
        return self.tool_spec_list
    
    def get_tool_config(self):
        return {
                "tools": self.tool_spec_list
        }

    def delete_tool(self, function_name):
        """
        Deletes a tool from the tool config and removes the monkey patched method from the class
        
        Parameters:
        - function_name (str) The name of the function to delete
        """
        
        if function_name:
            # Remove the monkey patched function from the class
            if hasattr(self.__class__, function_name):
                delattr(self.__class__, function_name)
            else:
                print(f"Warning: Function '{function_name}' not found in the class.")
            
            # Remove the tool specification from the list
            #for tool_spec in self.tool_spec_list:
            #    if tool_spec.get('toolSpec', {}).get('name') == function_name:
            #        self.tool_spec_list.remove(tool_spec)
            #        break
            #else:
            #    print(f"Warning: Tool specification for '{function_name}' not found in the tool_spec_list.")
            # Remove the tool specification from the list
            index = 0
            found = False
            while index < len(self.tool_spec_list):
                tool_spec = self.tool_spec_list[index]
                if tool_spec.get('toolSpec', {}).get('name') == function_name:
                    del self.tool_spec_list[index]
                    found = True
                    break
                index += 1
    
            if not found:
                print(f"Warning: Tool specification for '{function_name}' not found in the tool_spec_list.")                
        else:
            raise ValueError("Function name must be provided")

    def handle_tool_use(self, message):
        """
        Handles tool use
        
        Parameters:
        - message (dict) The message from Converse API
        
        Returns:
        - tool_result_message (dict) The tool result message
        
        """
        
        content = message["content"]
        
        tool_result_content_blocks = []
        
        for chunk in content:
            if "text" in chunk:
                print(f"Assistant: {chunk['text']}")
                
            if "toolUse" in chunk:
                tool = chunk["toolUse"]
                tool_use_id = tool["toolUseId"]
                tool_name = tool["name"]
                parameters = tool["input"]
                
                print(f"Tool Use: {tool_name}")
                print(f"Parameters: {parameters}")
                
                # Default message
                tool_result = f"Tool {tool_name} is not supported."
                
                # Call the appropriate tool
                for tool_spec in self.tool_spec_list:
                    if tool_name == tool_spec["toolSpec"]["name"]:
                        # Retrieve the method
                        tool = getattr(self, tool_name)
                        
                        # Call the method
                        try:
                            tool_result = tool(**parameters)
                        except Exception as e:
                            tool_result = f"Error occurred when calling {tool_name}: {e}"
                
                #Print the result, limit character output
                print(f"Tool Result: {str(tool_result)[:100]}")
                
                timestamp_chunk = self.create_timestamp_content_block(start_time=self.start_time)                 
                tool_result_content_block = {
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [

                            {
                                "text": str(tool_result)
                            },
                            timestamp_chunk
                        ]
                    }
                }
                
                tool_result_content_blocks.append(tool_result_content_block)
            
        # Final tool use message
        tool_result_message = {
            "role": "user",
            "content": tool_result_content_blocks
        }
        
        return tool_result_message
