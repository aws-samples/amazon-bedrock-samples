---
tags:
    - RAG/ Knowledge-Bases
    - RAG/ Data-Ingestion
    - API-Usage-Example
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/00-zero-setup-chat-with-your-document/chat_with_document_kb.ipynb){:target="_blank"}"

<h2>Chat with your document using Knowledge Bases for Amazon Bedrock - RetrieveAndGenerate API</h2>
 With `chat with your document` capability, you can securely ask questions on single documents, without the overhead of setting up a vector database or ingesting data, making it effortless for businesses to use their enterprise data. You only need to provide a relevant data file as input and choose your FM to get started.

For details around use cases and benefits, please refer to this [blogpost](#https://aws.amazon.com/blogs/machine-learning/knowledge-bases-in-amazon-bedrock-now-simplifies-asking-questions-on-a-single-document/).

<h3>Pre-requisites</h3>
<h5>Python 3.10</h5>
⚠ For this lab we need to run the notebook based on a Python 3.10 runtime. ⚠
<h3>Setup</h3>

Install following packages.


```python
%pip install --upgrade pip
%pip install --upgrade boto3
%pip install --upgrade botocore
%pip install pypdf
```


```python
<h2>restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

Before we begin, lets check the boto3 version, make sure its equal to or greater than `1.34.94`


```python
import boto3
boto3.__version__
```

Initialize client for Amazon Bedrock for accessing the `RetrieveAndGenerate` API.


```python
import boto3
import pprint
from botocore.client import Config

pp = pprint.PrettyPrinter(indent=2)
session = boto3.session.Session()
region = session.region_name
bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

bedrock_agent_client = boto3.client("bedrock-agent-runtime",
                              region_name=region,
                              config=bedrock_config,
                                    )
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
```

For data, you can either upload the document you want to chat with or point to the Amazon Simple Storage Service (Amazon S3) bucket location that contains your file. We provide you with both options in the notebook. However in both cases, the supported file formats are PDF, MD (Markdown), TXT, DOCX, HTML, CSV, XLS, and XLSX. Make that the file size does not exceed 10 MB and contains no more than 20K tokens. A token is considered to be a unit of text, such as a word, sub-word, number, or symbol, that is processed as a single entity. Due to the preset ingestion token limit, it is recommended to use a file under 10MB. However, a text-heavy file, that is much smaller than 10MB, can potentially breach the token limit.

<h3>Option 1 - Upload the document</h3>

In our example, we will use a pdf file.


```python
<h2>load pdf</h2>
from pypdf import PdfReader
<h2>creating a pdf reader object</h2>
file_name = "<path of your file such as file.pdf>" #path of the file on your local machine.
reader = PdfReader(file_name)
<h2>printing number of pages in pdf file</h2>
print(len(reader.pages))
text = ""
page_count = 1
for page in reader.pages:
    text+= f"\npage_{str(page_count)}\n {page.extract_text()}"
print(text)
```

<h3>Option 2 - Point to S3 location of your file</h3>
Make sure to replace the `bucket_name` and `prefix_file_name` to the location of your file.


```python
bucket_name = "<replace with your bucket name>"
prefix_file_name = "<replace with the file name in your bucket>" #include prefixes if any alongwith the file name.
document_s3_uri = f's3://{bucket_name}/{prefix_file_name}'

```

<h3>RetreiveAndGenerate API for chatting with your document</h3>
The code in the below cell, defines a Python function called `retrieveAndGenerate` that takes two optional arguments: `input` (the input text) and `sourceType` (the type of source to use, defaulting to "S3"). It also sets a default value for the `model_id` parameter.

The function constructs an Amazon Resource Name (ARN) for the specified model using the `model_id` and the `REGION` variable.

If the `sourceType` is "S3", the function calls the `retrieve_and_generate` method of the `bedrock_agent_client` object, passing in the input text and a configuration for retrieving and generating from external sources. The configuration specifies that the source is an S3 location, and it provides the S3 URI of the document.

If the `sourceType` is not "S3", the function calls the same `retrieve_and_generate` method, but with a different configuration. In this case, the source is specified as byte content, which includes a file name, content type (application/pdf), and the actual text data.


```python
def retrieveAndGenerate(input, sourceType="S3", model_id = "anthropic.claude-3-sonnet-20240229-v1:0"):
    model_arn = f'arn:aws:bedrock:{region}::foundation-model/{model_id}'
    if sourceType=="S3":
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'EXTERNAL_SOURCES',
                'externalSourcesConfiguration': {
                    'modelArn': model_arn,
                    "sources": [
                        {
                            "sourceType": sourceType,
                            "s3Location": {
                                "uri": document_s3_uri
                            }
                        }
                    ]
                }
            }
        )
    else:
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'EXTERNAL_SOURCES',
                'externalSourcesConfiguration': {
                    'modelArn': model_arn,
                    "sources": [
                        {
                            "sourceType": sourceType,
                            "byteContent": {
                                "identifier": file_name,
                                "contentType": "application/pdf",
                                "data": text,
                                }
                        }
                    ]
                }
            }
        )
```

If you want to chat with the document by uploading the file use `sourceType` as `BYTE_CONTENT` for pointing it to s3 bucket, use `sourceType` as `S3`.


```python
query = "Summarize the document"
response = retrieveAndGenerate(input=query, sourceType="BYTE_CONTENT")
generated_text = response['output']['text']
pp.pprint(generated_text)
```

<h2>Citations or source attributions</h2>
Lets retrieve the source attribution or citations for the above response.



```python
citations = response["citations"]
contexts = []
for citation in citations:
    retrievedReferences = citation["retrievedReferences"]
    for reference in retrievedReferences:
         contexts.append(reference["content"]["text"])

pp.pprint(contexts)
```

<h2>Next Steps</h2>
In this notebook, we covered how Knowledge Bases for Amazon Bedrock now simplifies asking questions on a single document. We also demonstrated how to configure and use this capability through the Amazon Bedrock - AWS SDK, showcasing the simplicity and flexibility of this feature, which provides a zero-setup solution to gather information from a single document, without setting up a vector database.

To further explore the capabilities of Knowledge Bases for Amazon Bedrock, refer to the following resources:

[Knowledge bases for Amazon Bedrock](#https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
