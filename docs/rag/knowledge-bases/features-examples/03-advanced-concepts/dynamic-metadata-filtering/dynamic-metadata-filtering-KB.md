---
tags:
    - RAG/ Metadata-Filtering
    - Agents/ Function Calling
    - RAG/ Knowledge-Bases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/03-advanced-concepts/dynamic-metadata-filtering/dynamic-metadata-filtering-KB.ipynb){:target="_blank"}"

<h2>Dynamic Metadata Filtering for Knowledge Bases for Amazon Bedrock</h2>

This notebook demonstrates how to implement dynamic metadata filtering for `Knowledge Bases for Amazon Bedrock` using the `tool use` (function calling) capability and `Pydantic` for data validation. By leveraging this approach, you can enhance the flexibility and accuracy of `retrieval-augmented generation` (RAG) applications, leading to more relevant and contextually appropriate AI-generated responses.

<h2>Overview</h2>

`Metadata filtering` is a powerful feature in Knowledge Bases for Amazon Bedrock that allows you to refine search results by pre-filtering the vector store based on custom metadata attributes. This approach narrows down the search space to the most relevant documents or passages, reducing noise and irrelevant information. However, manually constructing metadata filters can become challenging and error-prone, especially for complex queries or a large number of metadata attributes.

To address this challenge, we can leverage the power of `foundation models` (FMs) to create a more intuitive and user-friendly solution. This approach, which we call intelligent metadata filtering, uses `function calling` (also known as tool use) to intelligently extract metadata filters from natural language inputs. Function calling allows models to interact with external tools or functions, enhancing their ability to process and respond to complex queries.

By implementing intelligent metadata filtering using Amazon Bedrock and Pydantic, we can significantly enhance the flexibility and power of RAG applications. This approach allows for more intuitive querying of knowledge bases, leading to improved context recall and more relevant AI-generated responses.

<h3>Understanding Tool Use (Function Calling)</h3>

`Tool use`, also known as function calling, is a powerful feature in Amazon Bedrock that allows models to access external tools or functions to enhance their response generation capabilities. When you send a message to a model, you can provide definitions for one or more tools that could potentially help the model generate a response. If the model determines it needs a tool, it responds with a request for you to call the tool, including the necessary input parameters.

This feature enables models to leverage external data sources, perform calculations, or invoke other functionalities, significantly expanding their capabilities beyond pure text generation.

<h2>Prerequisites</h2>

Before proceeding, ensure you have:

1. An AWS account with access to Amazon Bedrock.
2. A Knowledge Base created in Amazon Bedrock with ingested data and metadata. If you do not have one setup, you can follow the instructions as mentioned in the [aws blogpost on metadata filtering with Knowledge Bases for Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/knowledge-bases-for-amazon-bedrock-now-supports-metadata-filtering-to-improve-retrieval-accuracy/).

<h2>Setup</h2>

First, let's set up the environment with the necessary imports and boto3 clients:


```python
%pip install --force-reinstall -q -r ../requirements.txt
```


```python
<h2># restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```


```python
%store -r kb_id_standard
```


```python
import json
import boto3
from typing import List, Optional
from pydantic import BaseModel, validator

session = boto3.session.Session()
region = session.region_name
bedrock = boto3.client("bedrock-runtime", region_name=region)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0" # "<add-model-id>"

<h2>KB with FAISS for metadata filtering</h2>
kb_id = kb_id_standard
```

<h2>Define Pydantic Models</h2>

We'll use Pydantic models to validate and structure our extracted entities:


```python
class Entity(BaseModel):
    Publisher: Optional[str]
    Year: Optional[int]

class ExtractedEntities(BaseModel):
    entities: List[Entity]

    @validator('entities', pre=True)
    def remove_duplicates(cls, entities):
        unique_entities = []
        seen = set()
        for entity in entities:
            entity_tuple = tuple(sorted(entity.items()))
            if entity_tuple not in seen:
                seen.add(entity_tuple)
                unique_entities.append(dict(entity_tuple))
        return unique_entities
```

<h2>Implement Entity Extraction using Tool Use</h2>

We'll define a tool for entity extraction with very basic instructions and use it with Amazon Bedrock:


```python
tool_name = "extract_entities"
tool_description = "Extract named entities from the text. If you are not 100% sure of the entity value, use 'unknown'."

tool_extract_entities = ["Publisher", "Year"]
tool_extract_property = ["entities"]

tool_entity_description = {
    "Publisher": {"type": "string", "description": "The publisher of the game. First alphabet is upper case."},
    "Year": {"type": "integer", "description": "The year when the game was released."}
}

tool_properties = {
    'tool_name':tool_name,
    'tool_description':tool_description,
    'tool_extract_entities':tool_extract_entities,
    'tool_extract_property':tool_extract_property,
    'tool_entity_description': tool_entity_description
}

def extract_entities(text, tool_properties):   
    tools = [{
            "toolSpec": {
                "name": tool_properties['tool_name'],
                "description": tool_properties['tool_description'],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": tool_properties['tool_entity_description'],
                                    "required": tool_properties['tool_extract_entities']
                                }
                            }
                        },
                        "required": tool_properties['tool_extract_property']
                    }
                }
            }
        }]
    
    response = bedrock.converse(
        modelId=MODEL_ID,
        inferenceConfig={
            "temperature": 0,
            "maxTokens": 4000
        },
        toolConfig={"tools": tools},
        messages=[{"role": "user", "content": [{"text": text}]}]
    )

    json_entities = None
    for content in response['output']['message']['content']:
        if "toolUse" in content and content['toolUse']['name'] == "extract_entities":
            json_entities = content['toolUse']['input']
            break

    if json_entities:
        return ExtractedEntities.parse_obj(json_entities)
    else:
        print("No entities found in the response.")
        return None
```

<h2>Construct Metadata Filter</h2>

Now, let's create a function to construct the metadata filter based on the extracted entities:


```python
def construct_metadata_filter(extracted_entities):
    if not extracted_entities or not extracted_entities.entities:
        return None

    entity = extracted_entities.entities[0]
    metadata_filter = {"andAll": []}

    if entity.Publisher and entity.Publisher != 'unknown':
        metadata_filter["andAll"].append({
            "equals": {
                "key": "Publisher",
                "value": entity.Publisher
            }
        })

    if entity.Year and entity.Year != 'unknown':
        metadata_filter["andAll"].append({
            "greaterThanOrEquals": {
                "key": "Year",
                "value": int(entity.Year)
            }
        })

    return metadata_filter if metadata_filter["andAll"] else None
```

<h2>Process Query and Retrieve Results</h2>

Finally, let's create a main function to process the query and retrieve results using the `Retrieve` API from Amazon Bedrock. This function will leverage the previously defined methods for entity extraction and metadata filter construction.

Note that this implementation demonstrates the use of the `Retrieve` API, but you can also leverage the `RetrieveAndGenerate` API to directly generate responses based on the retrieved context. The choice between these APIs depends on your specific use case and requirements.


```python
def process_query(text, tool_properties):
    extracted_entities = extract_entities(text, tool_properties)
    metadata_filter = construct_metadata_filter(extracted_entities)
    print('Here is the prepared metadata filters:')
    print(metadata_filter)

    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "filter": metadata_filter
            }
        },
        retrievalQuery={
            'text': text
        }
    )
    return response
```

<h2>Example Usage</h2>

You can test the implementation with the following example:


```python
text = "Provide a list of all video games published by Rockstar Games and released after 2010"
results = process_query(text, tool_properties)

<h2>Print results</h2>
print(results)
```

<h2>Handling Edge Cases</h2>

When implementing dynamic metadata filtering, it's important to consider and handle edge cases. Here are some ways you can address them:

If the function calling process fails to extract any metadata from the user query due to absence of filters or errors, you have several options:

1. `Proceed without filters`: This allows for a broad search but may reduce precision.
2. `Apply a default filter`: This can help maintain some level of filtering even when no specific metadata is extracted.
3. `Use the most common filter`: If you have statistics available on common user queries, you could apply the most frequently used filter.
4. `Strict Policy Handling`: For cases where you want to enforce stricter policies or adhere to specific responsible AI guidelines, you might choose not to process queries that don't yield metadata.

<h2>Performance Considerations</h2>

It's important to note that this dynamic approach introduces an additional FM call to extract metadata, which will increase both cost and latency. To mitigate this:

1. Consider using a faster, lighter FM for the metadata extraction step. This can help reduce latency and cost while still providing accurate entity extraction.
2. Implement caching mechanisms for common queries to avoid redundant FM calls.
3. Monitor and optimize the performance of your metadata extraction model regularly.

<h2>Cleanup</h2>

After you've finished experimenting with this solution, it's crucial to clean up your resources to avoid unnecessary charges. Please follow the detailed cleanup instructions provided in the `Clean up` section of the blog post: [Knowledge Bases for Amazon Bedrock now supports metadata filtering to improve retrieval accuracy](https://aws.amazon.com/blogs/machine-learning/knowledge-bases-for-amazon-bedrock-now-supports-metadata-filtering-to-improve-retrieval-accuracy/).

These steps will guide you through deleting your Knowledge Base, vector database, IAM roles, and sample datasets, ensuring that you don't incur any unexpected costs.

<h2>Conclusion</h2>

By implementing dynamic metadata filtering using Amazon Bedrock and Pydantic, we've significantly enhanced the flexibility and power of RAG applications. This approach allows for more intuitive querying of knowledge bases, leading to improved context recall and more relevant AI-generated responses.

As you explore this technique, remember to balance the benefits of dynamic filtering against the additional computational costs. We encourage you to try this method in your own RAG applications and share your experiences with the community.


<h2>End</h2>
