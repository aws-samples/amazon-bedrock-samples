import os

from agent import BaseAgent

from tool_groups.sql import SQL_TOOL_GROUP
from tool_groups.memory import MEMORY_TOOL_GROUP

memory_table_name = os.environ.get('DynamoDbMemoryTable', 'advtext2sql_memory_tb')
model_id = os.environ.get('BedrockModelId', 'anthropic.claude-3-sonnet-20240229-v1:0')

def lambda_handler(event, context):
    print(event)
    
    input_text = event["input_text"]
    
    # Initialize SQL agent
    print("Initializing agent")
    agent = BaseAgent(model_id=model_id, memory_table_name=memory_table_name)
    agent.add_tool_group(SQL_TOOL_GROUP)
    agent.add_tool_group(MEMORY_TOOL_GROUP)
    
    print("Invoking agent")
    response = agent.invoke_agent(input_text)
    
    print("Completed agent execution")
    print(response)
    
    return {
        "statusCode": 200,
        "body": response
    }