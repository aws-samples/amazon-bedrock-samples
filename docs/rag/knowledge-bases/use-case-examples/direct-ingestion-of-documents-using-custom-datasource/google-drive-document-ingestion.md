# Direct ingestion of Google Drive documents using a custom data source and the Document Level API (DLA)

With Document Level API (DLA), customers can now efficiently and cost-effectively ingest, update, or delete data directly from Amazon Bedrock Knowledge Bases using a single API call, without the need to perform a full sync with the data source periodically or after every change.

To read more about DLA, see the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-add.html)

In this example, we pull documents from google drive and then ingest them in our knowledge base using DLA.

## Pre-requisites
- You will need to create a knowledge base with a custom data source.  You can do this via the AWS console or follow the instructions in this notebook found in this repo at:   amazon-bedrock-samples/rag/knowledge-bases/features-examples/01-rag-concepts/01_create_ingest_documents_test_kb_multi_ds.ipynb
- Please note the knowledge base id and the data source id.
- You will need a Google Drive and some sample data.  You can create a free google account for this.  
- You will need to setup API access for Google Drive.  Instructions on how to do this are in this [pdf](./Google-Drive-API-Access.pdf).  Note: It's possible that these instructions may change as they refer to a third party product.

## Acquire Sample Data

We will use synthetic data for our document.  You can find a sample pdf in this repo under:

amazon-bedrock-samples/rag/knowledge-bases/features-examples/synthetic_dataset/octank_financial_10K.pdf


## Add the documents to Google Drive.

You will need a google account.  Go to https://workspace.google.com/products/drive/ and sign in.  Drag the pdf from your desktop to the drive.  When done it should look something like this:

![step 1](images/Google-drive-step-1.png)

<div class="alert alert-block alert-info">
<b>Note:</b> Please make sure to enable `Anthropic Claude 3 Sonnet` and,  `Titan Text Embeddings V2` model access in Amazon Bedrock Console.
<br> -------------------------------------------------------------------------------------------------------------------------------------------------------   </br>
    
Please run the notebook cell by cell instead of using "Run All Cells" option.
</div>

## Install dependencies


```python
# install the google client libraries
%pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
%pip install --force-reinstall -q -r ../../features-examples/requirements.txt  --quiet
%pip install --upgrade boto3
%pip install dotenv
%pip install PyPDF2

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
If you want to use environment variables then open the file 'example_dot_env' and fill in the appropriate values for your `KNOWLEDGE_BASE_ID` and `DOCUMENT_STORE_ID`.  Rename it to .env so the python interpreter will pick it up.  Otherwise you can hardcode the values below.
</div>


```python
from dotenv import load_dotenv
import os

load_dotenv()

kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
ds_id = os.environ.get("DOCUMENT_STORE_ID")

# if you don't want to use environment variables, uncomment the following and you can hard code the values here
# kb_id = "your-kb-id"
# ds_id = "your-ds-id"
```

## Generate document configs for the knowledge base.
We loop through the available files and create a 'document config' for each one.  In our example, we just have the one pdf file.  We store metadata for each document config.  This allows for filtering when we use the Retrieve API or the Retrieve and Generate API.

When you run the cell below, you'll be redirected to google to authenticate.  After authentication, it will read each ebook and store them to a list.


```python
from utilities import *
documents = [] # for this demo we are only looking for .txt or pdf files

files = list_gdrive_files()
for file in files:
    print(f"{file['name']} ({file['id']})")
    content = None
    if file['name'].endswith('.txt'):
        content = read_text_file(file['id'])
    elif file['name'].endswith('.pdf'):
        pdf_bytes, content = get_pdf_from_drive(file['id'])
    
    if content is None:
        print(f"Skipping {file['name']} as it is not a supported file type.")
    else: 
        document_id = file['name']
        doc = build_document_config(document_id, content, "MyProject")
        documents.append(doc)

print(f"Total number of documents: {len(documents)}")
```

# Ingest documents directly to the knowledge base using DLA
Note:  In this example we aren't considering queing or retry logic as we ingest documents.  


```python
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
query = 'What was the total operating lease liabilities and total sublease income of the Octank as of December 31, 2022?'    
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

Chunk 1:  \nThe following table summarizes Octank's lease portfolio as of December 31, 2021:\n| Lease Type | Total Lease Liability | Weighted-Average Remaining Lease Term |\n| --- | --- | --- |\n| Operating Leases | $50 million | 5 years |\n| Financing Leases | $30 million | 7 years |\n| Sales-Type Leases | $20 million | 3 years |\nIn addition to the above, it is important to note that Octank has adopted ASC 842, Leases, as of January 1, 2022. This new standard requires\nlessees to recognize a lease liability and a right-of-use (ROU) asset for all leases, with the exception of short-term leases. The new standard\nalso requires lessees to classify leases as either finance or operating leases, with finance leases being those that transfer substantially all of the\nrisks and rewards of ownership to the lessee.\nAs a result of adopting ASC 842, Octank has recorded a ROU asset of $100 million and a lease liability of $100 million as of January 1, 2022.\nThe company has also reviewed its lease portfolio and determined that all of its operating leases and financing leases should be classified as\nfinance leases under the new standard.\n\nIn conclusion, Octank has a significant lease portfolio that includes operating leases, financing leases, and sales-type leases.

Chunk 1 Location:  {'customDocumentLocation': {'id': 'octank_financial_10K.pdf'}, 'type': 'CUSTOM'}

Chunk 1 Score:  0.61955404

Chunk 1 Metadata:  {'x-amz-bedrock-kb-source-uri': 'octank_financial_10K.pdf', 'source': 'MyProject', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3ApRL5i5UBWLDVJrs7q2KT', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}

Chunk 2:  As\nof December 31, 2021, Octank has entered into operating leases with a total lease liability of $50 million and a weighted-average remaining\nlease term of 5 years.\nFinancing leases are leases in which the underlying asset is used in the normal course of business, but the lease payments are structured in a\nway that provides Octank with the option to purchase the underlying asset at the end of the lease term. At the end of the lease term, Octank has\nthe right to purchase the underlying asset for a nominal amount. As of December 31, 2021, Octank has entered into financing leases with a total\nlease liability of $30 million and a weighted-average remaining lease term of 7 years.\nSales-type leases are leases in which Octank is the lessor and the underlying asset is sold to the lessee at the beginning of the lease term. The\nlease payments are structured in a way that provides Octank with a profit or loss on the sale of the underlying asset. As of December 31, 2021,\nOctank has entered into sales-type leases with a total lease receivable of $20 million and a weighted-average remaining lease term of 3 years.

Chunk 2 Location:  {'customDocumentLocation': {'id': 'octank_financial_10K.pdf'}, 'type': 'CUSTOM'}

Chunk 2 Score:  0.6147984

Chunk 2 Metadata:  {'x-amz-bedrock-kb-source-uri': 'octank_financial_10K.pdf', 'source': 'MyProject', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AaKH5i5UBbj15VCY4nNCZ', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}

Chunk 3:  As of December 31, 2021,\nOctank has entered into sales-type leases with a total lease receivable of $20 million and a weighted-average remaining lease term of 3 years.\nThe following table summarizes Octank's lease portfolio as of December 31, 2021:\n| Lease Type | Total Lease Liability | Weighted-Average Remaining Lease Term |\n| --- | --- | --- |\n| Operating Leases | $50 million | 5 years |\n| Financing Leases | $30 million | 7 years |\n| Sales-Type Leases | $20 million | 3 years |\nIn addition to the above, it is important to note that Octank has adopted ASC 842, Leases, as of January 1, 2022. This new standard requires\nlessees to recognize a lease liability and a right-of-use (ROU) asset for all leases, with the exception of short-term leases. The new standard\nalso requires lessees to classify leases as either finance or operating leases, with finance leases being those that transfer substantially all of the\nrisks and rewards of ownership to the lessee.\nAs a result of adopting ASC 842, Octank has recorded a ROU asset of $100 million and a lease liability of $100 million as of January 1, 2022.

Chunk 3 Location:  {'customDocumentLocation': {'id': 'octank_financial_10K.pdf'}, 'type': 'CUSTOM'}

Chunk 3 Score:  0.6127239

Chunk 3 Metadata:  {'x-amz-bedrock-kb-source-uri': 'octank_financial_10K.pdf', 'source': 'MyProject', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AaaH5i5UBbj15VCY4nNCZ', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}

Chunk 4:  At the end of the lease term, Octank has\nthe right to purchase the underlying asset for a nominal amount. As of December 31, 2021, Octank has entered into financing leases with a total\nlease liability of $30 million and a weighted-average remaining lease term of 7 years.\nSales-type leases are leases in which Octank is the lessor and the underlying asset is sold to the lessee at the beginning of the lease term. The\nlease payments are structured in a way that provides Octank with a profit or loss on the sale of the underlying asset. As of December 31, 2021,\nOctank has entered into sales-type leases with a total lease receivable of $20 million and a weighted-average remaining lease term of 3 years.\nThe following table summarizes Octank's lease portfolio as of December 31, 2021:\n| Lease Type | Total Lease Liability | Weighted-Average Remaining Lease Term |\n| --- | --- | --- |\n| Operating Leases | $50 million | 5 years |\n| Financing Leases | $30 million | 7 years |\n| Sales-Type Leases | $20 million | 3 years |\nIn addition to the above, it is important to note that Octank has adopted ASC 842, Leases, as of January 1, 2022.

Chunk 4 Location:  {'customDocumentLocation': {'id': 'octank_financial_10K.pdf'}, 'type': 'CUSTOM'}

Chunk 4 Score:  0.6036647

Chunk 4 Metadata:  {'x-amz-bedrock-kb-source-uri': 'octank_financial_10K.pdf', 'source': 'MyProject', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3ApBL5i5UBWLDVJrs7q2KT', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}

Chunk 5:  By classifying,\nmonitoring, and reporting these funds separately from unrestricted cash, we aim to provide greater transparency and a more accurate\nrepresentation of our liquidity and financial position.\n\nLeases under NOTES TO CONSOLIDATED FINANCIAL STATEMENTS\nOctank Financial has several leases that are important to note in the consolidated financial statements. These leases include operating leases,\nfinancing leases, and sales-type leases. Each type of lease has its own unique characteristics and accounting treatment.\nOperating leases are leases in which the underlying asset is used in the normal course of business and the lease payments are classified as\noperating expenses on the income statement. At the end of the lease term, Octank does not have the right to purchase the underlying asset. As\nof December 31, 2021, Octank has entered into operating leases with a total lease liability of $50 million and a weighted-average remaining\nlease term of 5 years.\nFinancing leases are leases in which the underlying asset is used in the normal course of business, but the lease payments are structured in a\nway that provides Octank with the option to purchase the underlying asset at the end of the lease term. At the end of the lease term, Octank has\nthe right to purchase the underlying asset for a nominal amount.

Chunk 5 Location:  {'customDocumentLocation': {'id': 'octank_financial_10K.pdf'}, 'type': 'CUSTOM'}

Chunk 5 Score:  0.583498

Chunk 5 Metadata:  {'x-amz-bedrock-kb-source-uri': 'octank_financial_10K.pdf', 'source': 'MyProject', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AoxL5i5UBWLDVJrs7q2KT', 'x-amz-bedrock-kb-data-source-id': 'MXVGTRJ9JX'}



## Query the knowledge base
Here we query the knowledge base with a question about the pdf.  Notice the use of metadata to filter by document source.


```python
query = "What is the schedule of assets?"
region = 'us-east-1'
foundation_model = "anthropic.claude-3-haiku-20240307-v1:0"

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
                        "value": "MyProject"
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

## Example response

The schedule of assets is a financial statement schedule that provides a detailed breakdown of the company's assets. It includes information such as a list of the company's major customers, the carrying amounts and fair values of the company's financial assets, and the gross and net amounts of the company's impaired assets.

------- METADATA -------
octank_financial_10K.pdf 

