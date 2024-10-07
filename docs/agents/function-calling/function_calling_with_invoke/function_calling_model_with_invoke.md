---
tags:
    - Agents/ Function Calling
---

<!-- <h2>How to do function calling using InvokeModel API and model-specific prompting</h2> -->

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/function-calling/function_calling_with_invoke/function_calling_model_specific.ipynb){:target="_blank"}"

<h2>Overview</h2>

- **Tool calling with Anthropic Claude 3.5 Sonnet** We demonstrate how to define a single tool. In our case, for simulating a stock ticker symbol lookup tool `get_ticker_symbol` and allow the model to call this tool to return a a ticker symbol.
- **Tool calling with Meta Llama 3.1** We modify the prompts to fit Meta's suggested prompt format.
- **Tool calling with Mistral AI Large** We modify the prompts to fit Mistral's suggested prompt format.
- **Tool calling with Cohere Command R+** We modify the prompts to fit Cohere's suggested prompt format.

<h2>Context</h2>

This notebook demonstrates how we can use the `InvokeModel API` with external functions to support tool calling. 

Although `Converse` and `ConverseStream` provide a unified structured text action for simplifying the invocations to Amazon Bedrock LLMs, along with the use of `Tool` for function calling, some customers may choose to call `InvokeModel` or `InvokeModelWithResponseStream` supplying model-specific parameters and prompts. 

Most differentiated real-world applications require access to real-time data and the ability to interact with it. On their own, models do not have the ability to call external functions or APIs to bridge this gap. To solve this, function calling lets developers define a set of tools (external functions) the model has access to and, defines instructions the model uses to return a structured output that can be used to call the function. A tool definition includes its name, description and input schema. The model can be given a certain level of freedom when choosing to answer user requests using a set of tools. 

We cover the prompting components required to enable a model to call the correct tools based on a given input request.

<h2>Prerequisites</h2>

Before you can use Amazon Bedrock, you must carry out the following steps:

- Sign up for an AWS account (if you don't already have one) and IAM Role with the necessary permissions for Amazon Bedrock, see [AWS Account and IAM Role](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#new-to-aws){:target="_blank"}.
- Request access to the foundation models (FM) that you want to use, see [Request access to FMs](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#getting-started-model-access){:target="_blank"}. 
    

<h2>Setup</h2>

!!! info
    This notebook should work well with the Data Science 3.0 kernel (Python 3.10 runtime) in SageMaker Studio

Run the cells in this section to install the packages needed by this notebook.

```python
!pip install boto3 --quiet
!pip install botocore --quiet
!pip install beautifulsoup4 --quiet
!pip install lxml --quiet
```

<h3>Tool calling with Anthropic Claude 3.5 Sonnet</h3>

We set our tools and functions through Python functions.

We start by defining a tool for simulating a stock ticker symbol lookup tool (`get_ticker_symbol`). Note in our example we're just returning a constant ticker symbol for a select group of companies to illustrate the concept, but you could make it fully functional by connecting it to any stock or finance API.

This first example leverages Claude Sonnet 3.5 in the `us-west-2` region. Later, we continue with implementations using various other models available in Amazon Bedrock. The full list of models and supported regions can be found [here](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html). Ensure you have access to the models discussed at the beginning of the notebook. The models are invoked via `bedrock-runtime`.


```python
# Import necessary libraries
from bs4 import BeautifulSoup 
import boto3
import json


modelId = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
region = 'us-west-2'

bedrock = boto3.client(
    service_name = 'bedrock-runtime',
    region_name = region,
    )
```

<h3>Helper Functions & Prompt Templates</h3>

We define a few helper functions and tools that each model uses.

First, we define `ToolsList` class with a member function, namely `get_ticker_symbol`, which returns the ticker symbol of a limited set of companies. Note that there is nothing specific to the model used or Amazon Bedrock in these definitions.

!!! info
    You can add more functions in the `ToolsList` class for added capabilities. For instance, you can modify the function to call a finance API to retrieve stock information.

```python
# Define your tools
class ToolsList:
    # define get_ticker_symbol
    def get_ticker_symbol(company_name: str) -> str:
    
        if company_name.lower() == "general motors":
            return 'GM'
            
        elif company_name.lower() == "apple":
            return 'AAPL'
    
        elif company_name.lower() == "amazon":
            return 'AMZN'
    
        elif company_name.lower() == "3M":
            return 'MMM'
    
        elif company_name.lower() == "nvidia":
            return 'NVDA'
    
        else:
            return 'TickerNotFound'
```

The models we cover in this notebook support XML or JSON formatting to parse input prompts. We define a simple helper function converting a model's function choice into the XML format.


```python
# Format the functions results for input back to the model using XML in its response
def func_results_xml(tool_name, tool_return):
   return f"""
        <function_results>
            <result>
                <tool_name>{tool_name}</tool_name>
                <stdout>
                    {tool_return}
                </stdout>
            </result>
        </function_results>"""
```

We define a function to parse the model's XML output into readable text. Since each model returns a different response format (i.e. Anthropic Claude's completion can be retrieved by `response['content'][0]['text']` and Meta Llama 3.1 uses `response['generation']`). Further, we create equivalent functions for the other models covered.


```python
# Parses the output of Claude to extract the suggested function call and parameters
def parse_output_claude_xml(response):
    soup=BeautifulSoup(response['content'][0]['text'].replace('\n',''),"lxml")
    tool_name=soup.tool_name.string
    parameter_name=soup.parameters.contents[0].name
    parameter_value=soup.parameters.contents[0].string
    return (tool_name,{parameter_name:parameter_value})
```

Without `Converse`, models present some difference in their `InvokeModel API` around their hyperparameters. We define the function to invoke Anthropic models.


```python
# Claude 3 invocation function
def invoke_anthopic_model(bedrock_runtime, messages, max_tokens=512,top_p=1,temp=0):

    body=json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temp,
            "top_p": top_p,
            "stop_sequences":["</function_calls>"]
        }  
    )  
    
    response = bedrock_runtime.invoke_model(body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0")
    response_body = json.loads(response.get('body').read())

    return response_body
```

<h3>Tool calling with Anthropic Claude</h3>

We now define the system prompt provided to Claude when implementing function calling including several important components:

- An instruction describing the intent and setting the context for function calling.
- A detailed description of the tool(s) and expected parameters that Claude can suggest the use of.
- An example of the structure of the function call so that it can be parsed by the client code and ran.
- A directive to form a thought process before deciding on a function to call.
- The user query itself.

We supply `get_ticker_symbol` as a tool the model has access to respond to given type of query.


```python
system_prompt = """In this environment you have access to a set of tools you can use to answer the user's question.
    
    You may call them like this:
            
    <function_calls>
    <invoke>
    <tool_name>$TOOL_NAME</tool_name>
    <parameters>
    <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
    ...
    </parameters>
    </invoke>
    </function_calls>
            
    Here are the tools available:
    <tools>
    <tool_description>
    <tool_name>get_ticker_symbol</tool_name>
    <description>Gets the stock ticker symbol for a company searched by name. Returns str: The ticker symbol for the company stock. Raises TickerNotFound: if no matching ticker symbol is found.</description>
    <parameters>
    <parameter>
    <name>company_name</name>
    <type>string</type>
    <description>The name of the company.</description>
    </parameter>
    </parameters>
    </tool_description>
    </tools>
            
    Come up with a step by step plan for what steps should be taken, what functions should be called and in 
    what order. Place your thinking between <rationale> tags. Only create this rationale 1 time before 
    creating any other outputs.
            
    You will take in any outputs from called functions which will be in <function_results> tags and use 
    them to further suggests next steps and actions to take.

    If the question is unrelated to the tools available, then refuse to answer it and supply the explanation.
    """         
```

We use the Messages API covered [here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html). It manages the conversational exchanges between a user and an Anthropic Claude model (assistant). Anthropic trains Claude models to operate on alternating user and assistant conversational turns. When creating a new message, you specify the prior conversational turns with the messages parameter. The model then generates the next Message in the conversation. 

We prompt the model with a question within the scope of the tool.


```python
message_list = [{"role": 'user', "content": [{"type": "text", "text": f"""
    {system_prompt}
    Here is the user's question: <question>What is the ticker symbol of General Motors?</question>

    How do you respond to the user's question?"""}]
}]
```

We previously added `"</function_calls>"` to the list of stop sequences letting Claude end its output prior to generating this token representing a closing bracket. Given the query, the model correctly returns its rationale and the selected tool call. Evidently, the output follows the natural language description in the system prompt passed when calling the model.


```python
response = invoke_anthopic_model(bedrock, messages=message_list)
print(response['content'][0]['text'])

message_list.append({
        "role": 'assistant',
        "content": [
            {"type": "text", "text": response['content'][0]['text']}
        ]})
```

<h4>Executing the function and returning the result</h4>

With this `response`, we parse the returned XML to get the `tool_name`, along with the value for the required `parameter` infered by the model.


```python
tool_name, param = parse_output_claude_xml(response)
```

With the parsed tool information, we execute the Python function. We validate the correct ticket is returned. 


```python
try:
    tool_return=eval(tool_name)(**param)
    assert tool_return == "GM"
except AssertionError as e:
    tool_return=e
```

We need to place the function results in an input message to Claude with the following structure:

```
<function_results>
   <result>
        <tool_name>get_ticker_symbol</tool_name>
       <stdout>
           <<some_function_results>>
       </stdout>
   </result>
</function_results>
```

We format the output of our function and append the result to the message list.


```python
# Parse the XML results into a readable format
results=func_results_xml(tool_name,tool_return)

# Append result to the conversation flow
message_list.append({
        "role": 'user',
        "content": [
            {"type": "text", "text":f"""This is the final answer to the user question using the function 
            results. Do not output the name of the functions and tools used to get the answer {results}"""}
        ]})
```

Finally, we can get Claude to read the full conversation history that includes the initial instructions and the result of the actions it took. It can now respond to the user with the final answer to their query.


```python
response=invoke_anthopic_model(bedrock, messages=message_list)
print(response['content'][0]['text'])
```

We can see that Claude summarizes the results of the function given the context of the conversation history and answers our original question.

If asking a question outside the model's scope, the model refuses to answer. It is possible to modify the instructions so the model answers the question by relying on its internal knowledge.


```python
message_list = [{"role": 'user', "content": [{"type": "text", "text": f"""
    {system_prompt}
    Here is the user's question: <question>Who is the president of the US ?</question>

    How do you respond to the user's question?"""}]
}]

response = invoke_anthopic_model(bedrock, messages=message_list)
print(response['content'][0]['text'])
```

<h3>Tool calling with Meta Llama 3.1</h3>

Now we cover function calling using Meta Llama 3.1. We define the same function (`get_ticker_symbol`). We define the function calling the Bedrock InvokeModel API and supply the keys for the inference hyperparameters specific to Llama models.


```python
# Meta Llama 3 invocation function
bedrock = boto3.client('bedrock-runtime',region_name='us-west-2')

def invoke_llama_model(bedrock_runtime, messages, max_tokens=512,top_p=1,temp=0):
    
    body=json.dumps(
        {
            "max_gen_len": max_tokens,
            "prompt": messages,
            "temperature": temp,
            "top_p": top_p,
        }  
    )  
    
    response = bedrock_runtime.invoke_model(body=body, modelId="meta.llama3-70b-instruct-v1:0")
    response_body = json.loads(response.get('body').read())

    return response_body

```

We define Llama's system prompt based on Meta's own [documentation](https://llama.meta.com/docs/model-cards-and-prompt-formats/llama3_1/#built-in-tooling). We define our custom tools as a JSON dictionary


```python
from datetime import datetime

system_prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Cutting Knowledge Date: December 2023
    Today Date: {datetime.today().strftime('%Y-%m-%d')}

    When you receive a tool call response, use the output to format an answer to the orginal user question.

    You are a helpful assistant with tool calling capabilities.<|eot_id|><|start_header_id|>user<|end_header_id|>

    Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.
    
    Respond in the format {{\"name\": function name, \"parameters\": dictionary of argument name and its value}}. Do not use variables.
    If the question is unrelated to the tools available, then refuse to answer it and supply the explanation.
    
    {{
        "type": "function",
        "function": {{
        "name": "get_ticker_symbol",
        "description": "Returns the ticker symbol of a company if a user searches by its company name",
        "parameters": {{
            "type": "object",
            "properties": {{
            "company_name": {{
                "type": "string",
                "description": The name of the company."
            }}
            }},
            "required": ["company_name"]
        }}
        }}
    }}
"""
```

We supply the result to the message and invoke the model to summarize the result. The model correctly summarizes the conversation flow resulting from the initial query. 


```python
# Call LLama 3.1 and print response
message = f"""{system_prompt}
    Question: What is the symbol for Apple?<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

response = invoke_llama_model(bedrock, messages=message)
print(response['generation'])
```

Once we have the necessary tool call, we can follow a similar path to other models by executing the function, then returning the result to the model.

If asking a question outside the model's scope, the model refuses to answer. It is possible to modify the instructions so the model answers the question by relying on its internal knowledge.


```python
# Call LLama 3.1 and print response
message = f"""{system_prompt}
    Question: Who is the president of the US?<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

response = invoke_llama_model(bedrock, messages=message)
print(response['generation'])
```

<h3>Tool calling with Mistral AI Large</h3>

Now we cover function calling using Mistral. We define the same function (`get_ticker_symbol`). We define the function calling the Bedrock InvokeModel API and supply the keys for the inference hyperparameters specific to Mistral models.


```python
# Mistral Instruct invocation function
def invoke_mistral(bedrock_runtime, messages, max_tokens=512,top_p=1,temp=0):
    body=json.dumps(
        {
            "max_tokens": max_tokens,
            "prompt": messages,
            "temperature": temp,
            "top_p": top_p,
        }
    )
    
    response = bedrock_runtime.invoke_model(body=body, modelId="mistral.mistral-large-2402-v1:0")
    response_body = json.loads(response.get('body').read())

    return response_body
```

When invoking Mistral models, it is recommend to wrap input text in the following format: `<s>[INST] Instruction [/INST] Model answer</s>[INST] Follow-up instruction [/INST]` where `<s>` and `</s>` are special tokens for beginning of string (BOS) and end of string (EOS) while `[INST]` and `[/INST]` are regular strings. We will modify our JSON template to use these tags.

We define Mistral Large's system prompt following general prompting practices for tool calling as these details are abstracted away in Mistral's documentation. We define our custom tools as a JSON dictionary


```python
system_prompt =  """<s>[INST]
    In this environment you have access to a set of tools you can use to answer the user's question.
    
    Use this JSON object to call the tool. You may call them like this:
    
    {
        "function_calls": [
            {
                "invoke": {
                    "tool_name": "$TOOL_NAME",
                    "parameters": {
                        "company_name": "$PARAMETER_VALUE"
                    }
                }
            }
        ]
    }
    
    Here are the tools available:
    
    {
        "tools": [
            {
                "tool_description": {
                    "tool_name": "get_ticker_symbol",
                    "description": "Returns the ticker symbol of a company only if a user searches by its company name, not it's ticker symbol. Returns str: The ticker symbol for the company stock. Raises TickerNotFound: if no matching ticker symbol is found.",
                    "parameters": [
                        {
                            "name": "company_name",
                            "type": "string",
                            "description": "The name of the company."
                        }
                    ]
                }
            }
        ]
    }
    
    Choose one tool to use for your response. Do not use a tool if it is not required, it should match what the user requires. Only create this rationale 1 time before creating any other outputs.
    If the question is unrelated to the tools available, then refuse to answer it and supply the explanation. Else, provide the "function_calls" JSON object in your response.
    </s>[INST] 
    """
```

With our prompt defined that provides clear instructions, we can now test the model by invoking the Mistral model using the function we defined earlier


```python
# Call Mistral and print response
message = f"""{system_prompt}
    Question: What is the symbol for Amazon?
    [/INST]
    """
response = invoke_mistral(bedrock, messages=message)
print(response['outputs'][0]['text'])
```

Once we have the necessary tool call, we can follow a similar path to other models by executing the function, then returning the result to the model.

If asking a question outside the model's scope, the model refuses to answer. It is possible to modify the instructions so the model answers the question by relying on its internal knowledge.


```python
# Call Mistral and print response
message = f"""{system_prompt}
    Question: Who is the president of the US ?
    [/INST]
    """
response = invoke_mistral(bedrock, messages=message)
print(response['outputs'][0]['text'])
```

<h3>Tool calling with Cohere Command R+</h3>

Now we cover function calling using Mistral. We define the same function (`get_ticker_symbol`). We define the function calling the Bedrock InvokeModel API and supply the keys for the inference hyperparameters specific to Cohere models.


```python
# Cohere Command invocation function
def invoke_cohere(bedrock_runtime, messages, max_tokens=512,top_p=0.99,temp=0):

    body=json.dumps(
        {
            "max_tokens": max_tokens,
            "message": messages,
            "temperature": temp,
            "p": top_p,
        }  
    )  
    
    response = bedrock_runtime.invoke_model(body=body, modelId="cohere.command-r-plus-v1:0")
    response_body = json.loads(response.get('body').read())

    return response_body
```

When invoking the Command model, Cohere recommends using delimiters to denote instructions. More specifically, they recommend using clear headers by prepending them with `##`.

Similar to Mistral, we follow general prompting practices for tool calling as these details are abstracted away in Cohere's documentation. We define our custom tools as a key-value pairs.


```python
system_prompt = """

## Instructions

In this environment, you have access to a set of tools you can use to answer the user's question. Here are the tools available:

- get_ticker_symbol: Returns the ticker symbol of a company only if a user searches by its company name (ex. What is the ticker for Amazon?), not it's ticker symbol. The parameters required are:
    - company_name: The name of the company.

If the question is unrelated to the tools available, then refuse to answer it and supply the explanation.
Come up with a step-by-step plan for what actions should be taken. Only use a tool if it matches the user's query. Provide the rationale only once before creating any other outputs.

## Format
If you decide to use a tool, state the tool name and parameter you will pass it, nothing else. It must be in this format:

tool_name: tool_name
parameter": tool_param

I have provided some examples below on how you should respond. Do not include any preamble or extra information, just the tool used and the parameter passed to it.

## Examples
    
Example 1: 
    
tool_name: get_ticker_symbol
parameter": Apple
"""
```

With our prompt defined that provides clear instructions, we can now test the model by invoking the Cohere model using the function we defined earlier


```python
# Call Cohere and print response
message = f"""{system_prompt}
    ## Question
    What is the symbol for 3M?
    """
response = invoke_cohere(bedrock, messages=message)
print(response['text'])
```

Once we have the necessary tool call, we can follow a similar path to other models by executing the function, then returning the result to the model.

If asking a question outside the model's scope, the model refuses to answer. It is possible to modify the instructions so the model answers the question by relying on its internal knowledge.


```python
# Call Cohere and print response
message = f"""{system_prompt}
    ## Question
    Who is the president of the US ?
    """
response = invoke_cohere(bedrock, messages=message)
print(response['text'])
```

<h2>Next Steps</h2>

This notebook demonstrates function calling with the InvokeModel API, along with how to use these tools with multiple different types of models in Bedrock. We suggest experimenting with more complexity, including more tools for the models to use, orchestration loops, a detailed conversation history, and more complicated questions to ask each model that uses those tools in different ways. Ultimately, we do recommend leveraging the Converse API for most use cases and suggest diving deeper in the corresponding notebook examples.

<h2>Cleanup</h2>

This notebook does not require any cleanup or additional deletion of resources.