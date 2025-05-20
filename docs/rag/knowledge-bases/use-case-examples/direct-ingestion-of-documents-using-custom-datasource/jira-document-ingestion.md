# Direct ingestion of JIRA documents using a custom data source and the Document Level API (DLA)

With Document Level API (DLA), customers can now efficiently and cost-effectively ingest, update, or delete data directly from Amazon Bedrock Knowledge Bases using a single API call, without the need to perform a full sync with the data source periodically or after every change.

To read more about DLA, see the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-add.html)

In this example, we pull JIRA issues via an API then ingest these issues as documents in our knowledge base using DLA.

## Pre-requisites
- You will need to create a knowledge base with a custom data source.  You can do this via the AWS console or follow the instructions in this notebook found in this repo at:   amazon-bedrock-samples/rag/knowledge-bases/features-examples/01-rag-concepts/01_create_ingest_documents_test_kb_multi_ds.ipynb
- Please note the knowledge base id and the data source id.
- You will need a JIRA account with an API key and some sample data.  Instructions on how to do this are in this [pdf](./JIRA-API-Access.pdf).  Note: It's possible that these instructions may change as they refer to a third party product.



<div class="alert alert-block alert-info">
<b>Note:</b> Please make sure to enable `Anthropic Claude 3 Sonnet` and,  `Titan Text Embeddings V2` model access in Amazon Bedrock Console.
<br> -------------------------------------------------------------------------------------------------------------------------------------------------------   </br>
    
Please run the notebook cell by cell instead of using "Run All Cells" option.
</div>

## Install dependencies


```python
%pip install --force-reinstall -q -r ../../features-examples/requirements.txt  --quiet
%pip install --upgrade boto3
%pip install jira
%pip install dotenv
```

## Set System Path
We are using helper functions from the features-examples folder so we set the system path accordingly to allow for imports.


```python
import sys
from pathlib import Path
current_path = Path().resolve()
# modify path so we can access the utilities functions in the features-examples folder
current_path = current_path.parent.parent / 'features-examples'
if str(current_path) not in sys.path:
    sys.path.append(str(current_path))
print(sys.path)

```

## Setup the environment
<div class="alert alert-block alert-info">
Open the file 'example_dot_env' and fill in the appropriate values.<br/>  Rename it to .env so the python interpreter will pick it up.
</div>


```python
from dotenv import load_dotenv
import os

load_dotenv()

jira_server = os.environ.get("JIRA_SERVER")
email = os.environ.get("JIRA_EMAIL")
api_token = os.environ.get("JIRA_API_TOKEN")
kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
ds_id = os.environ.get("DOCUMENT_STORE_ID")

# if you don't want to use environment variables you can hardcode
# the values below and uncomment the code.
# jira_server = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# email = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# api_token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# kb_id = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# ds_id = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"


```

## Setup the JIRA connection



```python
from jira import JIRA

print(jira_server)
# Create JIRA connection
jira = JIRA(
    server=jira_server,
    basic_auth=(email, api_token)
)

# retrieve the jira projects
projects = jira.projects()


```

## Generate document configs for the knowledge base.
We loop through each JIRA project and create a 'document config' for each jira issue.  We store the project as metadata for each document.  This allows for filtering when we use the Retrieve API or the Retrieve and Generate API.


```python
from utilities import build_document_config
import json

documents = []

for project in projects:
    project_name = project.name
    print(f"Project: {project_name}")
    print(project)
    issues = jira.search_issues(f"project={project}")
    for issue in issues:
        document_config = build_document_config(issue.key, issue.fields.description, project_name)
        documents.append(document_config)

print(f"Total number of documents: {len(documents)}")

```

## Ingest documents directly to the knowledge base using DLA.
Note:  In this example we aren't considering queing or retry logic as we ingest documents.  


```python
from utils.knowledge_base_operators import ingest_documents_dla
# there is a limit of 10 documents per request, so we split the document into chunks.
for i in range(0, len(documents), 10):
    chunk = documents[i:i + 10]
    response = ingest_documents_dla(
            knowledge_base_id=kb_id,
            data_source_id=ds_id,
            documents=chunk 
        )
    print(response)
```

## Check the status of your documents
You should see a list of your documents with a status of 'indexed'


```python
import boto3
import pprint

bedrock_agent_client = boto3.client('bedrock-agent') 
# To fetch the status of documents
response = bedrock_agent_client.list_knowledge_base_documents(
    dataSourceId=ds_id,
    knowledgeBaseId=kb_id,
)
pprint.pprint(response)
```

## Query the knowledge base using the Retrieve API


```python
query = 'Do I have any security issues?'  # change this query to reflect the content of your jira issues.  
region = 'us-east-1'

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime') 

response_ret = bedrock_agent_runtime_client.retrieve(
    knowledgeBaseId=kb_id, 
    nextToken='string',
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults":5,
        } 
    },
    retrievalQuery={
        "text": query
    }
)

def response_print(retrieve_resp):
#structure 'retrievalResults': list of contents. Each list has content, location, score, metadata
    for num,chunk in enumerate(response_ret['retrievalResults'],1):
        print(f'Chunk {num}: ',chunk['content']['text'],end='\n'*2)
        print(f'Chunk {num} Location: ',chunk['location'],end='\n'*2)
        print(f'Chunk {num} Score: ',chunk['score'],end='\n'*2)
        print(f'Chunk {num} Metadata: ',chunk['metadata'],end='\n'*2)

response_print(response_ret)
```

## Below you can see examples of chunks pulled from the knowledge base using the retrieve API.  

Chunk 4:  "\nThe \"MFA on Root Account\" Trusted Advisor check has flagged that multi-factor authentication (MFA) is not enabled on the root user account for our AWS account. This poses a security risk.\n\nResources affected:\n- XXXXXXXXXXXXXXXXXXX  \n\nTo resolve this, we need to log in to the root account and activate an MFA device. AWS supports various MFA options like virtual authenticator apps or hardware security keys. Enabling MFA adds an extra layer of security by requiring a one-time code in addition to the root user password when logging in.\n"

Chunk 4 Location:  {'customDocumentLocation': {'id': 'KAN-67'}, 'type': 'CUSTOM'}

Chunk 4 Score:  0.38354945

Chunk 4 Metadata:  {'x-amz-bedrock-kb-source-uri': 'KAN-67', 'source': 'Acme Software', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AfMBwQ5UBv38PVEjahusy', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}

Chunk 5:  "\nAffected Resources: AWS::::Account:XXXXXXXXXX\n\nEnabling multi-factor authentication (MFA) for the root user account is a recommended security best practice. AWS Trusted Advisor flags this as a red alert if MFA is not enabled on the root account. \n\nMFA adds an extra layer of security by requiring a unique authentication code from a hardware or virtual device in addition to the account password when accessing the AWS Management Console and associated websites.\n\nTo resolve this:\n\n1. Sign in to the AWS Management Console as the root user\n2. Go to the IAM console\n3. In the navigation pane, choose Users\n4. Choose your root user entry\n5. On the Security Credentials tab, choose Multi-factor authentication (MFA)\n6. Follow the wizard to assign an MFA device\n"

Chunk 5 Location:  {'customDocumentLocation': {'id': 'KAN-57'}, 'type': 'CUSTOM'}

Chunk 5 Score:  0.38347003

Chunk 5 Metadata:  {'x-amz-bedrock-kb-source-uri': 'KAN-57', 'source': 'Acme Software', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AgsBwQ5UBv38PVEjanOuQ', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}


## Query the knowledge base and pass results to the foundation model using the Retrieve and Generate API
Here we query the knowledge base for issues involving security.  Notice the use of metadata to filter. The foundation model provides a nicely formatted response. 


```python


query = 'Do I have any security issues?'  # change this query to reflect the content of your jira issues.  
region = 'us-east-1'
foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime') 

result = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": query
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5,
                    "filter": {
                        "equals": {
                        "key": "source",
                        "value": "Acme Software"
                        }
                    }
                } 
            }

        }
    }
)
if result:
    print(result['output']['text'],end='\n'*2)
    print("------- METADATA -------")
    for citation in result['citations']:
        for ref in citation['retrievedReferences']:
            metadata = ref['metadata']
            print(metadata['x-amz-bedrock-kb-source-uri'], metadata['source'])


```

## Example Response

Based on the search results, you have security issues related to unrestricted access allowed by some of your security groups in AWS. Specifically, the search results mention that several of your security groups are allowing unrestricted incoming traffic (0.0.0.0/0) on certain ports, which poses a security risk. To resolve these issues, you should review the inbound rules for the affected security groups and restrict access to only trusted IP addresses or security groups for the required ports. Remove any rules allowing unrestricted 0.0.0.0/0 access on ports that should be restricted. Additionally, it is recommended to implement additional security measures like IP tables and regularly audit your security group rules to ensure they align with your security requirements.

