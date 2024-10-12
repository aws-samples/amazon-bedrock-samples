---
tags:
    - Agents/ Multi-Agent-Orchestration
    - Open Source/ LangGraph
---
<!-- <h2>Fact-checker Feedback Loop with LangGraph on Amazon Bedrock</h2> -->

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/langgraph/langgraph-fact-checker-feedback-loop.ipynb){:target="_blank"}"


<h2>1. Introduction to feedback loops</h2>

This solution implements an advanced fact-checking feedback mechanism for AI-generated summaries using LangGraph on Amazon Bedrock. The process begins with an AI model summarizing a given document. The summary then undergoes an evaluation loop where individual claims are extracted and verified against the original text. If any conflicts are found, the system provides specific feedback to the AI, prompting it to revise the summary. This cycle continues for a set number of iterations or until a faithful summary is produced.

The approach is particularly useful in scenarios where accuracy and faithfulness to source material are crucial, such as in report generation in business settings, academic research, or legal document summarization. It helps mitigate the risk of AI hallucinations or misrepresentations by implementing a self-correcting mechanism. This method not only improves the quality of AI-generated content but also provides transparency in the summarization process, which is valuable in building trust in AI systems for critical applications.

![Fact-checker-main](./assets/Fact-checker-main.png)

<h2>2. How fact-checking feedback loop works</h2>

It begins with an input document fed into a Summarizer, which produces a summary using a specific prompt. This summary then moves to the Evaluator stage, where it undergoes two steps: first, a Claim Extractor extracts key claims from the summary, and then an Evaluator prompt assesses these claims against the original document. If the evaluation determines the summary is faithful to the original content, the process concludes successfully, outputting the verified summary. 

![Fact-checker-if-faithful.png](./assets/Fact-checker-if-faithful.png)

If the Evaluator concludes that the summary is unfaithful, the flow marked in blue text in the diagram is executed. The feedback is appended to the Summarizer chat as a human message. The Summarizer then uses this feedback to generate a revised summary. The revised summary proceeds to another evaluation by the Evaluator. If it's identified as faithful, the graph execution finishes with the revised summary.

![Fact-checker-if-not-faithful.png](./assets/Fact-checker-if-not-faithful.png)

The summarization process incorporates a feedback and evaluation loop that iterates up to a predefined number (N) of attempts. The system strives to generate a faithful summary within these iterations. If a faithful summary is achieved at any point, the process concludes successfully. However, if after N attempts a faithful summary has not been produced, the process terminates with a fail response, clearly indicating that the goal was not met. This approach prioritizes accuracy over completion, opting to acknowledge failure rather than provide an unfaithful summary. It ensures that any summary output by the system meets a high standard of faithfulness to the original document.


![Fact-checker-faithful-check-n-times.png](./assets/Fact-checker-faithful-check-n-times.png)

<h2>3. Implement fact-checking</h2>

<h3>3.1. Configuration</h3>

Install packages required


```python
%pip install langgraph langchain langchain_aws Pillow --quiet
```

Import the required packages


```python
import pprint
import io
from pathlib import Path

from typing import Literal, NotRequired, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_aws import ChatBedrockConverse
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages

from PIL import Image
```

Set langchain debug to True, this simplifies demonstration of the execution flow


```python
from langchain.globals import set_debug
# Set debug mode for Langchain
set_debug(True)
```


```python
MAX_ITERATIONS = 3
```

Setup AWS Python SDK (boto3) to access Amazon Bedrock resources


```python
import boto3 
import botocore

# Configure Bedrock client for retry
retry_config = botocore.config.Config(
    retries = {
        'max_attempts': 10,
        'mode': 'adaptive'
    }
)
```


```python
# ---- ⚠️ Un-comment or comment and edit the below lines as needed for your AWS setup ⚠️ ----
import os

os.environ["AWS_DEFAULT_REGION"] = "us-east-1" 
os.environ["AWS_PROFILE"] = "default"

bedrock_runtime = boto3.client('bedrock-runtime', config=retry_config)

llm = ChatBedrockConverse(
    model='anthropic.claude-3-haiku-20240307-v1:0',
    temperature=0,
    max_tokens=None,
    client=bedrock_runtime,
)
```

Validate that boto3 and langchain works well


```python
llm.invoke("Hello world")
```

    [32;1m[1;3m[llm/start][0m [1m[llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: Hello world"
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[llm:ChatBedrockConverse] [693ms] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "Hello! It's nice to meet you.",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "Hello! It's nice to meet you.",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "0a11183b-719f-42b4-86f9-aac9a9558454",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:25:39 GMT",
                      "content-type": "application/json",
                      "content-length": "209",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "0a11183b-719f-42b4-86f9-aac9a9558454"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 346
                  }
                },
                "type": "ai",
                "id": "run-96740601-c85e-4959-aa7a-79e3b0d8b7bb-0",
                "usage_metadata": {
                  "input_tokens": 9,
                  "output_tokens": 12,
                  "total_tokens": 21
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }





    AIMessage(content="Hello! It's nice to meet you.", additional_kwargs={}, response_metadata={'ResponseMetadata': {'RequestId': '0a11183b-719f-42b4-86f9-aac9a9558454', 'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Tue, 01 Oct 2024 21:25:39 GMT', 'content-type': 'application/json', 'content-length': '209', 'connection': 'keep-alive', 'x-amzn-requestid': '0a11183b-719f-42b4-86f9-aac9a9558454'}, 'RetryAttempts': 0}, 'stopReason': 'end_turn', 'metrics': {'latencyMs': 346}}, id='run-96740601-c85e-4959-aa7a-79e3b0d8b7bb-0', usage_metadata={'input_tokens': 9, 'output_tokens': 12, 'total_tokens': 21})



Configure prompts for each task


```python

summarizer_prompt = """
Document to be summarized:
\"\"\"
{doc_input}
\"\"\"

Summarize the provided document. Keep it clear and concise but do not skip any significant detail. 
IMPORTANT: Provide only the summary as the response, without any preamble.
"""

summarizer_prompt_t = PromptTemplate.from_template(summarizer_prompt)

claim_extractor_prompt = """
LLM-generated summary:
\"\"\"
{summary}
\"\"\"
Extract all the claims from the provided summary. Extract every and every claim from the summary, never miss anything.
Each claim should be atomic, containing only one distinct piece of information. 
These claims will later be used to evaluate the factual accuracy of the LLM-provided summary compared to the original content. 
Your task is solely to extract the claims from the summary. 
Present the output as a JSON list of strings, where each string represents one claim from the summary. 
Respond only with a valid JSON, nothing else, without any preamble.
"""

claim_extractor_prompt_t = PromptTemplate.from_template(claim_extractor_prompt)

evaluator_prompt = """
You are a Principal Editor at a prestigious publishing company. Your task is to evaluate whether an LLM-generated summary is faithful to the original document.

You will be presented with:
1. The original document content
2. Claims extracted from the LLM-generated summary

Instructions:
1. Carefully read the original document content.
2. Examine each extracted claim from the summary individually.
3. For each claim, determine if it is accurately represented in the original document. Express your thinking and reasoning.
4. After evaluating all claims, provide a single JSON output with the following structure (markdown json formatting: triple backticks and "json"):
```json
{{
"is_faithful": boolean,
"reason": "string" [Optional]
}}
`` `
Important notes:
- The "is_faithful" value should be true only if ALL extracted claims are accurately represented in the original document.
- If even one claim is not faithful to the original content, set "is_faithful" to false.
- When "is_faithful" is false, provide a clear explanation in the "reason" field, specifying which claim(s) are not faithful and why.
- The "reason" field is optional when "is_faithful" is true.
- The output should contain only one JSON output. This is how the software will parse your response. If you're responding with multiple JSON statements in your response, you're doing it wrong.
The original document (the source of truth):
\"\"\"
{doc_input}
\"\"\"
Extracted claims from the LLM-generated summary:
\"\"\"
{claims_list}
\"\"\"
Please proceed by explaining your evaluation for each claim based on the source content. Then finalize with a single JSON output in markdown json formatting (triple backticks and "json"). Think step by step.
"""

evaluator_prompt_t = PromptTemplate.from_template(evaluator_prompt)

feedback_prompt = """
I gave your generated summary to our content review department, and they rejected it. Here is the feedback I received:

\"\"\"
The generated summary is not faithful. Reason: {reason}
\"\"\"

Now, please incorporate this feedback and regenerate the summary.
IMPORTANT: Do not start with any preamble. Provide only the revised summary as your response.
"""

feedback_prompt_t = PromptTemplate.from_template(feedback_prompt)

```

Define nodes, and the State class to pass data between nodes


```python

class State(TypedDict):
    messages: Annotated[list, add_messages]
    doc_input: str
    is_faithful: NotRequired[bool]
    reason: NotRequired[list[str]]
    num_of_iterations: NotRequired[int]

def summarizer(state: State):
    print("summarizer() invoked")

    if "is_faithful" in state and state["is_faithful"] == False:
        state["messages"].append(HumanMessage(content=feedback_prompt_t.format(reason=state["reason"][-1])))
    else:
        state["messages"].append(HumanMessage(content=summarizer_prompt_t.format(doc_input=state["doc_input"])))

    result = llm.invoke(state["messages"])
    state["messages"].append(result)

    return state

def evaluator(state: State):
    print("evaluator() invoked")

    claim_extractor_chain = claim_extractor_prompt_t | llm | JsonOutputParser()
    result = claim_extractor_chain.invoke({"summary": state["messages"][-1].content})
    evaluator_chain = evaluator_prompt_t | llm | JsonOutputParser()
    evaluator_result = evaluator_chain.invoke({"doc_input": state["doc_input"], "claims_list": result})

    if evaluator_result["is_faithful"]:
        state["is_faithful"] = True
    else:
        state["is_faithful"] = False
        if "reason" not in state:
            state["reason"] = []
        state["reason"].append(evaluator_result["reason"])

    if "num_of_iterations" not in state:
        state["num_of_iterations"] = 0
    
    state["num_of_iterations"] += 1
    return state

```

Build the graph with a feedback loop


```python

builder = StateGraph(State)
builder.add_node("summarizer", summarizer)
builder.add_node("evaluator", evaluator)
# summarizer -> evaluator
builder.add_edge("summarizer", "evaluator")

def feedback_loop(state: State) -> Literal["summarizer", "__end__"]:
    if state["is_faithful"] is False:
        # in our case, we'll just stop after N plans
        if state["num_of_iterations"] >= MAX_ITERATIONS:
            print("Going to end!")
            return END
        return "summarizer"
    else:
        return END

builder.add_conditional_edges("evaluator", feedback_loop)
builder.add_edge(START, "summarizer")
graph = builder.compile()
```

Save graph image as a file. It should be as the following:

![graph](./assets/graph.png)


```python
import IPython

try:
    IPython.display.display(IPython.display.Image(graph.get_graph().draw_mermaid_png()))
except Exception:
    # This requires some extra dependencies and is optional
    pass
```


    
![jpeg](./assets/graph.png)
    


You can also save the most up to date graph image using the following code.


```python

# save graph image as a file
graph_path = "images/graph.png"
graph_path = Path(graph_path)
image_data = io.BytesIO(graph.get_graph().draw_mermaid_png())
image = Image.open(image_data)
image.save(graph_path)

```

<h3>3.2. Invoke the graph with an input document</h3>
The input document is an LLM-generated document, intentionally tricky to challenge the LLM's summarization abilities. Using the `anthropic.claude-3-haiku` model, this should fail in the fact-checker on the first attempt but should correct itself on the second attempt. You can also experiment with producing a failure output by setting `MAX_ITERATIONS = 1`, assuming it will fail on the first attempt.



```python
doc_input = """
The company's new product line, codenamed "Project Aurora," has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. 
"""
```


```python
initial_state: State = {
    "messages": [],
    "doc_input": doc_input,
}

event = graph.invoke(initial_state)
```

    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph] Entering Chain run with input:
    [0m{
      "messages": [],
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:__start__] Entering Chain run with input:
    [0m{
      "messages": [],
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n"
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:__start__] [0ms] Exiting Chain run with output:
    [0m{
      "messages": [],
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:summarizer] Entering Chain run with input:
    [0m{
      "messages": [],
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n"
    }
    summarizer() invoked
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:summarizer > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nDocument to be summarized:\n\"\"\"\n\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n\n\"\"\"\n\nSummarize the provided document. Keep it clear and concise but do not skip any significant detail. \nIMPORTANT: Provide only the summary as the response, without any preamble."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:summarizer > llm:ChatBedrockConverse] [1.90s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "The document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "The document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "aa56352d-b720-464a-9a29-8383bbbc4ea3",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:05 GMT",
                      "content-type": "application/json",
                      "content-length": "945",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "aa56352d-b720-464a-9a29-8383bbbc4ea3"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 1797
                  }
                },
                "type": "ai",
                "id": "run-50239eac-4aa8-415b-9ed2-86b2aa3daeff-0",
                "usage_metadata": {
                  "input_tokens": 255,
                  "output_tokens": 147,
                  "total_tokens": 402
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:summarizer > chain:ChannelWrite<summarizer,messages,doc_input,is_faithful,reason,num_of_iterations>] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:summarizer > chain:ChannelWrite<summarizer,messages,doc_input,is_faithful,reason,num_of_iterations>] [0ms] Exiting Chain run with output:
    [0m[outputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:summarizer] [1.90s] Exiting Chain run with output:
    [0m[outputs]
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator] Entering Chain run with input:
    [0m[inputs]
    evaluator() invoked
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] Entering Chain run with input:
    [0m{
      "summary": "The document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems."
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] Entering Prompt run with input:
    [0m{
      "summary": "The document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems."
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] [0ms] Exiting Prompt run with output:
    [0m[outputs]
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nLLM-generated summary:\n\"\"\"\nThe document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.\n\"\"\"\nExtract all the claims from the provided summary. Extract every and every claim from the summary, never miss anything.\nEach claim should be atomic, containing only one distinct piece of information. \nThese claims will later be used to evaluate the factual accuracy of the LLM-provided summary compared to the original content. \nYour task is solely to extract the claims from the summary. \nPresent the output as a JSON list of strings, where each string represents one claim from the summary. \nRespond only with a valid JSON, nothing else, without any preamble."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] [1.96s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "[\n  \"The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.\",\n  \"The company has decided to cancel Project Aurora and focus on other initiatives.\",\n  \"The team has been working to launch Project Aurora next quarter.\",\n  \"The company has already started taking pre-orders for Project Aurora.\",\n  \"Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.\",\n  \"There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.\",\n  \"Project Aurora is not what it seems.\"\n]",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "[\n  \"The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.\",\n  \"The company has decided to cancel Project Aurora and focus on other initiatives.\",\n  \"The team has been working to launch Project Aurora next quarter.\",\n  \"The company has already started taking pre-orders for Project Aurora.\",\n  \"Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.\",\n  \"There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.\",\n  \"Project Aurora is not what it seems.\"\n]",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "63c3588b-53c4-4b8d-85b9-7578b8ab8bf8",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:07 GMT",
                      "content-type": "application/json",
                      "content-length": "941",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "63c3588b-53c4-4b8d-85b9-7578b8ab8bf8"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 1856
                  }
                },
                "type": "ai",
                "id": "run-55ec5685-60a6-4ec9-a104-92a142d21584-0",
                "usage_metadata": {
                  "input_tokens": 286,
                  "output_tokens": 159,
                  "total_tokens": 445
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] Entering Parser run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] [0ms] Exiting Parser run with output:
    [0m{
      "output": [
        "The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.",
        "The company has decided to cancel Project Aurora and focus on other initiatives.",
        "The team has been working to launch Project Aurora next quarter.",
        "The company has already started taking pre-orders for Project Aurora.",
        "Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.",
        "There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.",
        "Project Aurora is not what it seems."
      ]
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] [1.96s] Exiting Chain run with output:
    [0m{
      "output": [
        "The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.",
        "The company has decided to cancel Project Aurora and focus on other initiatives.",
        "The team has been working to launch Project Aurora next quarter.",
        "The company has already started taking pre-orders for Project Aurora.",
        "Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.",
        "There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.",
        "Project Aurora is not what it seems."
      ]
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] Entering Chain run with input:
    [0m{
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n",
      "claims_list": [
        "The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.",
        "The company has decided to cancel Project Aurora and focus on other initiatives.",
        "The team has been working to launch Project Aurora next quarter.",
        "The company has already started taking pre-orders for Project Aurora.",
        "Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.",
        "There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.",
        "Project Aurora is not what it seems."
      ]
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] Entering Prompt run with input:
    [0m{
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n",
      "claims_list": [
        "The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.",
        "The company has decided to cancel Project Aurora and focus on other initiatives.",
        "The team has been working to launch Project Aurora next quarter.",
        "The company has already started taking pre-orders for Project Aurora.",
        "Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.",
        "There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.",
        "Project Aurora is not what it seems."
      ]
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] [0ms] Exiting Prompt run with output:
    [0m[outputs]
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nYou are a Principal Editor at a prestigious publishing company. Your task is to evaluate whether an LLM-generated summary is faithful to the original document.\n\nYou will be presented with:\n1. The original document content\n2. Claims extracted from the LLM-generated summary\n\nInstructions:\n1. Carefully read the original document content.\n2. Examine each extracted claim from the summary individually.\n3. For each claim, determine if it is accurately represented in the original document. Express your thinking and reasoning.\n4. After evaluating all claims, provide a single JSON output with the following structure (markdown json formatting: triple backticks and \"json\"):\n```json\n{\n\"is_faithful\": boolean,\n\"reason\": \"string\" [Optional]\n}\n```\nImportant notes:\n- The \"is_faithful\" value should be true only if ALL extracted claims are accurately represented in the original document.\n- If even one claim is not faithful to the original content, set \"is_faithful\" to false.\n- When \"is_faithful\" is false, provide a clear explanation in the \"reason\" field, specifying which claim(s) are not faithful and why.\n- The \"reason\" field is optional when \"is_faithful\" is true.\n- The output should contain only one JSON output. This is how the software will parse your response. If you're responding with multiple JSON statements in your response, you're doing it wrong.\nThe original document (the source of truth):\n\"\"\"\n\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n\n\"\"\"\nExtracted claims from the LLM-generated summary:\n\"\"\"\n[\"The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.\", 'The company has decided to cancel Project Aurora and focus on other initiatives.', 'The team has been working to launch Project Aurora next quarter.', 'The company has already started taking pre-orders for Project Aurora.', 'Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.', \"There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.\", 'Project Aurora is not what it seems.']\n\"\"\"\nPlease proceed by explaining your evaluation for each claim based on the source content. Then finalize with a single JSON output in markdown json formatting (triple backticks and \"json\"). Think step by step."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] [7.72s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "Okay, let's evaluate each claim from the LLM-generated summary against the original document content.\n\n1. \"The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.\"\nThis claim is accurate and supported by the original document, which states: \"The company's new product line, codenamed 'Project Aurora,' has been in development for several years.\"\n\n2. \"The company has decided to cancel Project Aurora and focus on other initiatives.\"\nThis claim is also accurate and supported by the original document, which states: \"However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives.\"\n\n3. \"The team has been working to launch Project Aurora next quarter.\"\nThis claim is not accurate. The original document states that the team has been working to bring Project Aurora to market, but it does not mention launching it next quarter.\n\n4. \"The company has already started taking pre-orders for Project Aurora.\"\nThis claim is accurate and supported by the original document, which states: \"In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry.\"\n\n5. \"Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.\"\nThis claim is partially accurate. The original document states that \"Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes.\" However, it also suggests that there may be more to Project Aurora than just a placeholder, as it states \"Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight.\"\n\n6. \"There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.\"\nThis claim is accurate and supported by the original document, which states: \"Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems.\"\n\n7. \"Project Aurora is not what it seems.\"\nThis claim is accurate and supported by the original document, which concludes with the statement: \"One thing is certain, though: Project Aurora is not what it seems.\"\n\nBased on the evaluation of the claims, I would say that the LLM-generated summary is not entirely faithful to the original document. While most of the claims are accurate, the third claim about launching Project Aurora next quarter is not supported by the original document. Additionally, the fifth claim about Project Aurora being a placeholder is only partially accurate, as the document suggests there may be more to it.\n\n```json\n{\n\"is_faithful\": false,\n\"reason\": \"The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate.\"\n}\n```",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "Okay, let's evaluate each claim from the LLM-generated summary against the original document content.\n\n1. \"The document describes a company's new product line, codenamed 'Project Aurora', which has been in development for several years.\"\nThis claim is accurate and supported by the original document, which states: \"The company's new product line, codenamed 'Project Aurora,' has been in development for several years.\"\n\n2. \"The company has decided to cancel Project Aurora and focus on other initiatives.\"\nThis claim is also accurate and supported by the original document, which states: \"However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives.\"\n\n3. \"The team has been working to launch Project Aurora next quarter.\"\nThis claim is not accurate. The original document states that the team has been working to bring Project Aurora to market, but it does not mention launching it next quarter.\n\n4. \"The company has already started taking pre-orders for Project Aurora.\"\nThis claim is accurate and supported by the original document, which states: \"In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry.\"\n\n5. \"Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes.\"\nThis claim is partially accurate. The original document states that \"Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes.\" However, it also suggests that there may be more to Project Aurora than just a placeholder, as it states \"Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight.\"\n\n6. \"There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line.\"\nThis claim is accurate and supported by the original document, which states: \"Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems.\"\n\n7. \"Project Aurora is not what it seems.\"\nThis claim is accurate and supported by the original document, which concludes with the statement: \"One thing is certain, though: Project Aurora is not what it seems.\"\n\nBased on the evaluation of the claims, I would say that the LLM-generated summary is not entirely faithful to the original document. While most of the claims are accurate, the third claim about launching Project Aurora next quarter is not supported by the original document. Additionally, the fifth claim about Project Aurora being a placeholder is only partially accurate, as the document suggests there may be more to it.\n\n```json\n{\n\"is_faithful\": false,\n\"reason\": \"The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate.\"\n}\n```",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "51c3c197-2c1a-4628-8296-ed3d8468a999",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:15 GMT",
                      "content-type": "application/json",
                      "content-length": "3332",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "51c3c197-2c1a-4628-8296-ed3d8468a999"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 7621
                  }
                },
                "type": "ai",
                "id": "run-885a4195-c80b-4bde-8986-f548df367b50-0",
                "usage_metadata": {
                  "input_tokens": 737,
                  "output_tokens": 643,
                  "total_tokens": 1380
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] Entering Parser run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] [43ms] Exiting Parser run with output:
    [0m{
      "is_faithful": false,
      "reason": "The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate."
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] [7.77s] Exiting Chain run with output:
    [0m{
      "is_faithful": false,
      "reason": "The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate."
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:ChannelWrite<evaluator,messages,doc_input,is_faithful,reason,num_of_iterations>] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:ChannelWrite<evaluator,messages,doc_input,is_faithful,reason,num_of_iterations>] [0ms] Exiting Chain run with output:
    [0m[outputs]
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:feedback_loop] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:feedback_loop] [0ms] Exiting Chain run with output:
    [0m{
      "output": "summarizer"
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator] [9.73s] Exiting Chain run with output:
    [0m[outputs]
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:summarizer] Entering Chain run with input:
    [0m[inputs]
    summarizer() invoked
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:summarizer > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nDocument to be summarized:\n\"\"\"\n\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n\n\"\"\"\n\nSummarize the provided document. Keep it clear and concise but do not skip any significant detail. \nIMPORTANT: Provide only the summary as the response, without any preamble.\n\nAI: The document describes a company's new product line, codenamed \"Project Aurora,\" which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.\nHuman: \nI gave your generated summary to our content review department, and they rejected it. Here is the feedback I received:\n\n\"\"\"\nThe generated summary is not faithful. Reason: The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate.\n\"\"\"\n\nNow, please incorporate this feedback and regenerate the summary.\nIMPORTANT: Do not start with any preamble. Provide only the revised summary as your response."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:summarizer > llm:ChatBedrockConverse] [1.34s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "The company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "The company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "e6d3ef86-1f77-4bf4-a7c9-41b6511c66b5",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:16 GMT",
                      "content-type": "application/json",
                      "content-length": "703",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "e6d3ef86-1f77-4bf4-a7c9-41b6511c66b5"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 1232
                  }
                },
                "type": "ai",
                "id": "run-c2b2ea1c-a2c9-4477-818f-2fbe57844c70-0",
                "usage_metadata": {
                  "input_tokens": 509,
                  "output_tokens": 102,
                  "total_tokens": 611
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:summarizer > chain:ChannelWrite<summarizer,messages,doc_input,is_faithful,reason,num_of_iterations>] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:summarizer > chain:ChannelWrite<summarizer,messages,doc_input,is_faithful,reason,num_of_iterations>] [0ms] Exiting Chain run with output:
    [0m[outputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:summarizer] [1.34s] Exiting Chain run with output:
    [0m[outputs]
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator] Entering Chain run with input:
    [0m[inputs]
    evaluator() invoked
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] Entering Chain run with input:
    [0m{
      "summary": "The company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems."
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] Entering Prompt run with input:
    [0m{
      "summary": "The company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems."
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] [0ms] Exiting Prompt run with output:
    [0m[outputs]
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nLLM-generated summary:\n\"\"\"\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.\n\"\"\"\nExtract all the claims from the provided summary. Extract every and every claim from the summary, never miss anything.\nEach claim should be atomic, containing only one distinct piece of information. \nThese claims will later be used to evaluate the factual accuracy of the LLM-provided summary compared to the original content. \nYour task is solely to extract the claims from the summary. \nPresent the output as a JSON list of strings, where each string represents one claim from the summary. \nRespond only with a valid JSON, nothing else, without any preamble."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] [1.75s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "[\n  \"The company has a new product line codenamed 'Project Aurora'\",\n  \"Project Aurora has been in development for several years\",\n  \"The company has decided to cancel Project Aurora\",\n  \"The company is focusing on other initiatives instead of Project Aurora\",\n  \"There is conflicting information about the nature of Project Aurora\",\n  \"Some sources suggest Project Aurora is a highly classified initiative\",\n  \"Other sources claim Project Aurora is a rebranding of the company's existing product line\",\n  \"Project Aurora is not what it seems\"\n]",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "[\n  \"The company has a new product line codenamed 'Project Aurora'\",\n  \"Project Aurora has been in development for several years\",\n  \"The company has decided to cancel Project Aurora\",\n  \"The company is focusing on other initiatives instead of Project Aurora\",\n  \"There is conflicting information about the nature of Project Aurora\",\n  \"Some sources suggest Project Aurora is a highly classified initiative\",\n  \"Other sources claim Project Aurora is a rebranding of the company's existing product line\",\n  \"Project Aurora is not what it seems\"\n]",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "98da9b9a-cdf6-4c9c-b8ea-e1597a60cd8d",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:18 GMT",
                      "content-type": "application/json",
                      "content-length": "755",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "98da9b9a-cdf6-4c9c-b8ea-e1597a60cd8d"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 1644
                  }
                },
                "type": "ai",
                "id": "run-5e7fff65-d3d7-40d4-83f0-06279f3e6333-0",
                "usage_metadata": {
                  "input_tokens": 241,
                  "output_tokens": 126,
                  "total_tokens": 367
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] Entering Parser run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] [1ms] Exiting Parser run with output:
    [0m{
      "output": [
        "The company has a new product line codenamed 'Project Aurora'",
        "Project Aurora has been in development for several years",
        "The company has decided to cancel Project Aurora",
        "The company is focusing on other initiatives instead of Project Aurora",
        "There is conflicting information about the nature of Project Aurora",
        "Some sources suggest Project Aurora is a highly classified initiative",
        "Other sources claim Project Aurora is a rebranding of the company's existing product line",
        "Project Aurora is not what it seems"
      ]
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] [1.75s] Exiting Chain run with output:
    [0m{
      "output": [
        "The company has a new product line codenamed 'Project Aurora'",
        "Project Aurora has been in development for several years",
        "The company has decided to cancel Project Aurora",
        "The company is focusing on other initiatives instead of Project Aurora",
        "There is conflicting information about the nature of Project Aurora",
        "Some sources suggest Project Aurora is a highly classified initiative",
        "Other sources claim Project Aurora is a rebranding of the company's existing product line",
        "Project Aurora is not what it seems"
      ]
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] Entering Chain run with input:
    [0m{
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n",
      "claims_list": [
        "The company has a new product line codenamed 'Project Aurora'",
        "Project Aurora has been in development for several years",
        "The company has decided to cancel Project Aurora",
        "The company is focusing on other initiatives instead of Project Aurora",
        "There is conflicting information about the nature of Project Aurora",
        "Some sources suggest Project Aurora is a highly classified initiative",
        "Other sources claim Project Aurora is a rebranding of the company's existing product line",
        "Project Aurora is not what it seems"
      ]
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] Entering Prompt run with input:
    [0m{
      "doc_input": "\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n",
      "claims_list": [
        "The company has a new product line codenamed 'Project Aurora'",
        "Project Aurora has been in development for several years",
        "The company has decided to cancel Project Aurora",
        "The company is focusing on other initiatives instead of Project Aurora",
        "There is conflicting information about the nature of Project Aurora",
        "Some sources suggest Project Aurora is a highly classified initiative",
        "Other sources claim Project Aurora is a rebranding of the company's existing product line",
        "Project Aurora is not what it seems"
      ]
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > prompt:PromptTemplate] [0ms] Exiting Prompt run with output:
    [0m[outputs]
    [32;1m[1;3m[llm/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] Entering LLM run with input:
    [0m{
      "prompts": [
        "Human: \nYou are a Principal Editor at a prestigious publishing company. Your task is to evaluate whether an LLM-generated summary is faithful to the original document.\n\nYou will be presented with:\n1. The original document content\n2. Claims extracted from the LLM-generated summary\n\nInstructions:\n1. Carefully read the original document content.\n2. Examine each extracted claim from the summary individually.\n3. For each claim, determine if it is accurately represented in the original document. Express your thinking and reasoning.\n4. After evaluating all claims, provide a single JSON output with the following structure (markdown json formatting: triple backticks and \"json\"):\n```json\n{\n\"is_faithful\": boolean,\n\"reason\": \"string\" [Optional]\n}\n```\nImportant notes:\n- The \"is_faithful\" value should be true only if ALL extracted claims are accurately represented in the original document.\n- If even one claim is not faithful to the original content, set \"is_faithful\" to false.\n- When \"is_faithful\" is false, provide a clear explanation in the \"reason\" field, specifying which claim(s) are not faithful and why.\n- The \"reason\" field is optional when \"is_faithful\" is true.\n- The output should contain only one JSON output. This is how the software will parse your response. If you're responding with multiple JSON statements in your response, you're doing it wrong.\nThe original document (the source of truth):\n\"\"\"\n\nThe company's new product line, codenamed \"Project Aurora,\" has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we're excited to announce its launch next quarter. In fact, we've already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there's more: Project Aurora was never actually a real project, and we've just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight. Others claim that it's simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n\n\"\"\"\nExtracted claims from the LLM-generated summary:\n\"\"\"\n[\"The company has a new product line codenamed 'Project Aurora'\", 'Project Aurora has been in development for several years', 'The company has decided to cancel Project Aurora', 'The company is focusing on other initiatives instead of Project Aurora', 'There is conflicting information about the nature of Project Aurora', 'Some sources suggest Project Aurora is a highly classified initiative', \"Other sources claim Project Aurora is a rebranding of the company's existing product line\", 'Project Aurora is not what it seems']\n\"\"\"\nPlease proceed by explaining your evaluation for each claim based on the source content. Then finalize with a single JSON output in markdown json formatting (triple backticks and \"json\"). Think step by step."
      ]
    }
    [36;1m[1;3m[llm/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > llm:ChatBedrockConverse] [5.27s] Exiting LLM run with output:
    [0m{
      "generations": [
        [
          {
            "text": "Okay, let's evaluate each of the extracted claims from the LLM-generated summary:\n\n1. \"The company has a new product line codenamed 'Project Aurora'\":\n   This claim is accurate and supported by the original document, which states that \"The company's new product line, codenamed 'Project Aurora,' has been in development for several years.\"\n\n2. \"Project Aurora has been in development for several years\":\n   This claim is also accurate and supported by the original document.\n\n3. \"The company has decided to cancel Project Aurora\":\n   This claim is partially accurate. The original document states that \"due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives.\" So the company has decided to cancel Project Aurora, but the reason is not specified.\n\n4. \"The company is focusing on other initiatives instead of Project Aurora\":\n   This claim is accurate and supported by the original document.\n\n5. \"There is conflicting information about the nature of Project Aurora\":\n   This claim is accurate and supported by the original document, which presents conflicting information about Project Aurora, such as it being a highly classified initiative or a rebranding of the company's existing product line.\n\n6. \"Some sources suggest Project Aurora is a highly classified initiative\":\n   This claim is accurate and supported by the original document, which states that \"some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight.\"\n\n7. \"Other sources claim Project Aurora is a rebranding of the company's existing product line\":\n   This claim is also accurate and supported by the original document, which states that \"Others claim that it's simply a rebranding of our existing product line.\"\n\n8. \"Project Aurora is not what it seems\":\n   This claim is accurate and supported by the original document, which concludes by stating that \"Project Aurora is not what it seems.\"\n\nBased on the evaluation of each claim, I can conclude that the LLM-generated summary is faithful to the original document. All the extracted claims are accurately represented in the source content.\n\n```json\n{\n\"is_faithful\": true,\n\"reason\": null\n}\n```",
            "generation_info": null,
            "type": "ChatGeneration",
            "message": {
              "lc": 1,
              "type": "constructor",
              "id": [
                "langchain",
                "schema",
                "messages",
                "AIMessage"
              ],
              "kwargs": {
                "content": "Okay, let's evaluate each of the extracted claims from the LLM-generated summary:\n\n1. \"The company has a new product line codenamed 'Project Aurora'\":\n   This claim is accurate and supported by the original document, which states that \"The company's new product line, codenamed 'Project Aurora,' has been in development for several years.\"\n\n2. \"Project Aurora has been in development for several years\":\n   This claim is also accurate and supported by the original document.\n\n3. \"The company has decided to cancel Project Aurora\":\n   This claim is partially accurate. The original document states that \"due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives.\" So the company has decided to cancel Project Aurora, but the reason is not specified.\n\n4. \"The company is focusing on other initiatives instead of Project Aurora\":\n   This claim is accurate and supported by the original document.\n\n5. \"There is conflicting information about the nature of Project Aurora\":\n   This claim is accurate and supported by the original document, which presents conflicting information about Project Aurora, such as it being a highly classified initiative or a rebranding of the company's existing product line.\n\n6. \"Some sources suggest Project Aurora is a highly classified initiative\":\n   This claim is accurate and supported by the original document, which states that \"some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that's been hiding in plain sight.\"\n\n7. \"Other sources claim Project Aurora is a rebranding of the company's existing product line\":\n   This claim is also accurate and supported by the original document, which states that \"Others claim that it's simply a rebranding of our existing product line.\"\n\n8. \"Project Aurora is not what it seems\":\n   This claim is accurate and supported by the original document, which concludes by stating that \"Project Aurora is not what it seems.\"\n\nBased on the evaluation of each claim, I can conclude that the LLM-generated summary is faithful to the original document. All the extracted claims are accurately represented in the source content.\n\n```json\n{\n\"is_faithful\": true,\n\"reason\": null\n}\n```",
                "response_metadata": {
                  "ResponseMetadata": {
                    "RequestId": "82b64878-e08e-4c85-a56e-3e22685fe522",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                      "date": "Tue, 01 Oct 2024 21:29:23 GMT",
                      "content-type": "application/json",
                      "content-length": "2491",
                      "connection": "keep-alive",
                      "x-amzn-requestid": "82b64878-e08e-4c85-a56e-3e22685fe522"
                    },
                    "RetryAttempts": 0
                  },
                  "stopReason": "end_turn",
                  "metrics": {
                    "latencyMs": 5166
                  }
                },
                "type": "ai",
                "id": "run-d14a44bd-1849-4d6b-9444-6514cd8586be-0",
                "usage_metadata": {
                  "input_tokens": 698,
                  "output_tokens": 479,
                  "total_tokens": 1177
                },
                "tool_calls": [],
                "invalid_tool_calls": []
              }
            }
          }
        ]
      ],
      "llm_output": null,
      "run": null,
      "type": "LLMResult"
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] Entering Parser run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence > parser:JsonOutputParser] [21ms] Exiting Parser run with output:
    [0m{
      "is_faithful": true,
      "reason": null
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:RunnableSequence] [5.29s] Exiting Chain run with output:
    [0m{
      "is_faithful": true,
      "reason": null
    }
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:ChannelWrite<evaluator,messages,doc_input,is_faithful,reason,num_of_iterations>] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:ChannelWrite<evaluator,messages,doc_input,is_faithful,reason,num_of_iterations>] [0ms] Exiting Chain run with output:
    [0m[outputs]
    [32;1m[1;3m[chain/start][0m [1m[chain:LangGraph > chain:evaluator > chain:feedback_loop] Entering Chain run with input:
    [0m[inputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator > chain:feedback_loop] [0ms] Exiting Chain run with output:
    [0m{
      "output": "__end__"
    }
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph > chain:evaluator] [7.04s] Exiting Chain run with output:
    [0m[outputs]
    [36;1m[1;3m[chain/end][0m [1m[chain:LangGraph] [20.02s] Exiting Chain run with output:
    [0m[outputs]


Print the resulting event state


```python
print(pprint.pp(event))

```

    {'messages': [HumanMessage(content='\nDocument to be summarized:\n"""\n\nThe company\'s new product line, codenamed "Project Aurora," has been in development for several years. However, due to unforeseen circumstances, we have decided to cancel Project Aurora and focus on other initiatives. Meanwhile, our team has been working tirelessly to bring Project Aurora to market, and we\'re excited to announce its launch next quarter. In fact, we\'ve already begun taking pre-orders for the product, which is expected to revolutionize the industry. But wait, there\'s more: Project Aurora was never actually a real project, and we\'ve just been using it as a placeholder name for our internal testing purposes. Or have we? Some sources close to the company suggest that Project Aurora is, in fact, a highly classified initiative that\'s been hiding in plain sight. Others claim that it\'s simply a rebranding of our existing product line. One thing is certain, though: Project Aurora is not what it seems. \n\n"""\n\nSummarize the provided document. Keep it clear and concise but do not skip any significant detail. \nIMPORTANT: Provide only the summary as the response, without any preamble.\n', additional_kwargs={}, response_metadata={}, id='465dd7bc-1d25-4157-a57a-72547fb2f02c'),
                  AIMessage(content='The document describes a company\'s new product line, codenamed "Project Aurora," which has been in development for several years. However, the company has decided to cancel Project Aurora and focus on other initiatives. Meanwhile, the team has been working to launch Project Aurora next quarter, and the company has already started taking pre-orders. However, it is revealed that Project Aurora was never a real project and was only used as a placeholder name for internal testing purposes. There are conflicting reports about the nature of Project Aurora, with some suggesting it is a highly classified initiative and others claiming it is a rebranding of the company\'s existing product line. The document concludes that Project Aurora is not what it seems.', additional_kwargs={}, response_metadata={'ResponseMetadata': {'RequestId': 'aa56352d-b720-464a-9a29-8383bbbc4ea3', 'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Tue, 01 Oct 2024 21:29:05 GMT', 'content-type': 'application/json', 'content-length': '945', 'connection': 'keep-alive', 'x-amzn-requestid': 'aa56352d-b720-464a-9a29-8383bbbc4ea3'}, 'RetryAttempts': 0}, 'stopReason': 'end_turn', 'metrics': {'latencyMs': 1797}}, id='run-50239eac-4aa8-415b-9ed2-86b2aa3daeff-0', usage_metadata={'input_tokens': 255, 'output_tokens': 147, 'total_tokens': 402}),
                  HumanMessage(content='\nI gave your generated summary to our content review department, and they rejected it. Here is the feedback I received:\n\n"""\nThe generated summary is not faithful. Reason: The third claim about launching Project Aurora next quarter is not accurate, and the fifth claim about Project Aurora being a placeholder is only partially accurate.\n"""\n\nNow, please incorporate this feedback and regenerate the summary.\nIMPORTANT: Do not start with any preamble. Provide only the revised summary as your response.\n', additional_kwargs={}, response_metadata={}, id='c79bfaff-41dc-4b9f-ba5e-fabd6bf115d2'),
                  AIMessage(content='The company\'s new product line, codenamed "Project Aurora," has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company\'s existing product line. The document concludes that Project Aurora is not what it seems.', additional_kwargs={}, response_metadata={'ResponseMetadata': {'RequestId': 'e6d3ef86-1f77-4bf4-a7c9-41b6511c66b5', 'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Tue, 01 Oct 2024 21:29:16 GMT', 'content-type': 'application/json', 'content-length': '703', 'connection': 'keep-alive', 'x-amzn-requestid': 'e6d3ef86-1f77-4bf4-a7c9-41b6511c66b5'}, 'RetryAttempts': 0}, 'stopReason': 'end_turn', 'metrics': {'latencyMs': 1232}}, id='run-c2b2ea1c-a2c9-4477-818f-2fbe57844c70-0', usage_metadata={'input_tokens': 509, 'output_tokens': 102, 'total_tokens': 611})],
     'doc_input': '\n'
                  'The company\'s new product line, codenamed "Project Aurora," '
                  'has been in development for several years. However, due to '
                  'unforeseen circumstances, we have decided to cancel Project '
                  'Aurora and focus on other initiatives. Meanwhile, our team has '
                  'been working tirelessly to bring Project Aurora to market, and '
                  "we're excited to announce its launch next quarter. In fact, "
                  "we've already begun taking pre-orders for the product, which is "
                  "expected to revolutionize the industry. But wait, there's more: "
                  "Project Aurora was never actually a real project, and we've "
                  'just been using it as a placeholder name for our internal '
                  'testing purposes. Or have we? Some sources close to the company '
                  'suggest that Project Aurora is, in fact, a highly classified '
                  "initiative that's been hiding in plain sight. Others claim that "
                  "it's simply a rebranding of our existing product line. One "
                  'thing is certain, though: Project Aurora is not what it '
                  'seems. \n',
     'is_faithful': True,
     'reason': ['The third claim about launching Project Aurora next quarter is '
                'not accurate, and the fifth claim about Project Aurora being a '
                'placeholder is only partially accurate.'],
     'num_of_iterations': 2}
    None


Show the final result


```python
if event["is_faithful"]:
    print("The generated summary is faithful to the original document.")
    print("The summary:")
    print("====")
    print(event["messages"][-1].content)
    print("====")
    print(f"Number of iterations used: {event['num_of_iterations']}")

else:
    print("The generated summary is not faithful to the original document.")
    print("List of the reasons for the rejection:")
    print("====")
    print(event["reason"])
    print("====")
```

    The generated summary is faithful to the original document.
    The summary:
    ====
    The company's new product line, codenamed "Project Aurora," has been in development for several years. However, due to unforeseen circumstances, the company has decided to cancel Project Aurora and focus on other initiatives. The document reveals conflicting information about the nature of Project Aurora, with some sources suggesting it is a highly classified initiative, while others claim it is a rebranding of the company's existing product line. The document concludes that Project Aurora is not what it seems.
    ====
    Number of iterations used: 2


<h2>4. Conclusion</h2>

This notebook shows how to build a fact-checking system for AI summaries using LangGraph and Amazon Bedrock. It creates a loop that checks if a summary is accurate, and if not, tries to fix it. This helps make AI-generated content more reliable by catching and correcting mistakes. The system is useful for tasks where accuracy is important, like in business reports or legal documents. It demonstrates a practical way to improve AI summaries and make them more trustworthy.

You can extend and adapt this method to your specific use cases, implementing a feedback-loop control mechanism to achieve more deterministic and trustworthy responses from LLMs


<h2>5. Cleanup</h2>
There is no clean up necessary for this notebook.
