---
tags:
    - RAG/ Knowledge-Bases
    - Prompt-Engineering
    - RAG/ Data-Ingestion
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/01-rag-concepts/02_managed_rag_custom_prompting_and_no_of_results.ipynb){:target="_blank"}"

<h2>RetrieveAndGenerate API - Fully managed RAG</h2>

In this module, you'll learn how to improve the Foundation Model (FM) generations by controlling the maximum no. of results retrieved and performing custom prompting in Knowledge bases (KB) for Amazon Bedrock.

This module contains:

1. [Overview](#1-Overview)

2. [Pre-requisites](#2-Pre-requisites)

3. [How to leverage maximum number of results](#3-how-to-leverage-the-maximum-number-of-results-feature)

4. [How to use custom prompting](#4-how-to-use-the-custom-prompting-feature)

<h2>Overview</h2>

<h3>Maximum no. of results</h3>
The maximum number of results option gives you control over the number of search results to be retrieved from the vector store and passed to the FM for generating the answer. This allows you to customize the amount of background information provided for generation, thereby giving more context for complex questions or less for simpler questions. It allows you to fetch up to 100 results. This option helps improve the likelihood of relevant context, thereby improving the accuracy and reducing the hallucination of the generated response.


<h3>Custom prompting</h3>

As for the custom knowledge base prompt template allows you to replace the default prompt template with your own to customize the prompt that’s sent to the model for response generation. This allows you to customize the tone, output format, and behavior of the FM when it responds to a user’s question. With this option, you can fine-tune terminology to better match your industry or domain (such as healthcare or legal). Additionally, you can add custom instructions and examples tailored to your specific workflows.


<h4>Notes:</h4>
- You are going to use ```RetrieveAndGenerate``` API to illustrate the differences before and after utilizing the features. This API converts queries into embeddings, searches the knowledge base, and then augments the foundation model prompt with the search results as context information and returns the FM-generated response to the question. The output of the ```RetrieveAndGenerate``` API includes the generated response, source attribution as well as the retrieved text chunks.

- For this module, we will use the Anthropic Claude 3 Haiku model as our FM to work with the max no. of results and prompt customization features

<h2>Pre-requisites</h2>
Before being able to answer the questions, the documents must be processed and stored in a knowledge base. For this notebook, we use a `synthetic dataset for 10K financial reports` to create the Knowledge Bases for Amazon Bedrock. 

1. Upload your documents (data source) to Amazon S3 bucket.
2. Knowledge Bases for Amazon Bedrock using [01_create_ingest_documents_test_kb_multi_ds.ipynb](/knowledge-bases/01-rag-concepts/01_create_ingest_documents_test_kb_multi_ds.ipynb)
3. Note the Knowledge Base ID


<h2>Setup</h2>


```python
%pip install --force-reinstall -q -r ../requirements.txt
```


```python
<h2>restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

<h3>Initialize boto3 client</h3>
Through out the notebook, we are going to utilise RetrieveAndGenerate to test knowledge base features.


```python
import json
import boto3
import pprint
from botocore.exceptions import ClientError
from botocore.client import Config

<h2>Create boto3 session</h2>
sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name

<h2>Create bedrock agent client</h2>
bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}, region_name=region_name)
bedrock_agent_client = boto3_session.client("bedrock-agent-runtime",
                              config=bedrock_config)

<h2>Define FM to be used for generations </h2>
model_id = "anthropic.claude-3-haiku-20240307-v1:0" # we will be using Anthropic Claude 3 Haiku throughout the notebook
model_arn = f'arn:aws:bedrock:{region_name}::foundation-model/{model_id}'

```


```python
%store -r kb_id
<h2>kb_id = "<<knowledge_base_id>>" # Replace with your knowledge base id here.</h2>
```

<h3>Understanding RetrieveAndGenerate API</h3>

The `numberOfResults` parameter in the given function determines the number of search results that will be retrieved from the knowledge base and included in the prompt provided to the model for generating an answer. Specifically, it will fetch the top `max_results` number of documents or search results that most closely match the given query.

The `textPromptTemplate` parameter is a string that serves as a template for the prompt that will be provided to the model. In this case, the `default_prompt` is being used as the template. This template includes placeholders (`$search_results$` and `$output_format_instructions$`) that will be replaced with the actual search results and any output format instructions, respectively, before being passed to the model.


```python
<h2>Stating the default knowledge base prompt</h2>
default_prompt = """
You are a question answering agent. I will provide you with a set of search results.
The user will provide you with a question. Your job is to answer the user's question using only information from the search results. 
If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. 
Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion.
                            
Here are the search results in numbered order:
$search_results$

$output_format_instructions$
"""

def retrieve_and_generate(query, kb_id, model_arn, max_results, prompt_template = default_prompt):
    response = bedrock_agent_client.retrieve_and_generate(
            input={
                'text': query
            },
        retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': kb_id,
            'modelArn': model_arn, 
            'retrievalConfiguration': {
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results # will fetch top N documents which closely match the query
                    }
                },
                'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': prompt_template
                        }
                    }
            }
        }
    )
    return response

```

<h3>How to leverage the maximum number of results feature</h3>

In some use cases; the FM responses might be lacking enough context to provide relevant answers or relying that it couldn't find the requested info. Which could be fixed by modifying the maximum number of retrieved results.

In the following example, we are going to run the following query with a few number of results (5):
\
```Provide a list of risks for Octank financial in bulleted points.```



```python
def print_generation_results(response, print_context = True):
    generated_text = response['output']['text']
    print('Generated FM response:\n')
    print(generated_text)
    
    if print_context is True:
        ## print out the source attribution/citations from the original documents to see if the response generated belongs to the context.
        citations = response["citations"]
        contexts = []
        for citation in citations:
            retrievedReferences = citation["retrievedReferences"]
            for reference in retrievedReferences:
                contexts.append(reference["content"]["text"])
    
        print('\n\n\nRetrieved Context:\n')
        pprint.pp(contexts)

```


```python
query = """Provide a list of risks for Octank financial in numbered list without description."""

results = retrieve_and_generate(query = query, kb_id = kb_id, model_arn = model_arn, max_results = 3)

print_generation_results(results)
```


By modifying the no of retrived results to **10**, you should be able to get more results leading to comprehensive response.


```python
#Using higher number of max results

results = retrieve_and_generate(query = query, kb_id = kb_id, model_arn = model_arn, max_results = 10)

print_generation_results(results)
```

<h3>How to use the custom prompting feature</h3>

You can also customize the default prompt with your own prompt based on the use case. This feature would help adding more context to the FM, require specific output format, languages and others.

Let's give it a try using the SDK:


<h4>Example 1 -Using the same query example, we can default the FM to output to a different language like German:</h4>
\
**Note**: After removing ```$output_format_instructions$``` from the default prompt, the citation from the generated response is removed.


```python
<h2>Example 1</h2>
custom_prompt = """
You are a question answering agent. I will provide you with a set of search results. 
The user will provide you with a question. Your job is to answer the user's question using only information from the search results.
If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question.
Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion.
                            
Here are the search results in numbered order:
$search_results$

Unless asked otherwise, draft your answer in German language.
"""

results = retrieve_and_generate(query = query, kb_id = kb_id, model_arn = model_arn, max_results = 10, prompt_template = custom_prompt)

print_generation_results(results, print_context = False)
```


<h4>Example 2 - output the results in JSON format</h4>


```python
<h2>Example 2</h2>
custom_prompt = """
You are a question answering agent. I will provide you with a set of search results.
The user will provide you with a question. Your job is to answer the user's question using only information from the search results.
If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. 
Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion.
                            
Here are the search results in numbered order:
$search_results$

Please provide a concise response (in millions) using a JSON format.

"""

results = retrieve_and_generate(query = query, kb_id = kb_id, model_arn = model_arn, max_results = 10, prompt_template = custom_prompt)

print_generation_results(results,print_context = False)
```

<div class="alert alert-block alert-warning">
<b>Note:</b> Remember to delete KB, OSS index and related IAM roles and policies to avoid incurring any charges.
</div>
