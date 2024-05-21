# Custom integration with knowledge base

The agent integrates with the knowledge base without an explicit association to it. Essentially, based on the paths invoked in the openapi schema, it can choose to query the vector DB directly by filtering or the knowledge base through both filtering and semantic similarity. This is useful when you want more control over invocations of the knowledge base.

## Dataset

This example assumes a dataset with these fields - review (string), rating (number), timestamp (number), reviewers (string list).

We create the following metadata file for each of the text chunks (review) in the knowledge base.

The timestamp is in epoch format so date filters using ```greaterThan/lessThan``` operators can be used since Bedrock KB doesn't support date type currently.

In addition, string list can be filtered using the ```in``` operator. This can be used to implement document level access controls in OpenSearch Serverless. Each document can have a role attribute containing the list of roles that can access the document.

```json
{"metadataAttributes": {"rating": 4.0, "timestamp": 1588615855070, "reviewers": ["lebron", "jokic", "curry"]}}
```

## Knowledge Base integration

An [openapi schema](openapischema.json) is used to define the APIs that are callable by the agent.

The first API ```(/reviews/{count}/start_date/{start_date}/end_date/{end_date})``` takes in as arguments the number of results to return, the start date and the end date of the documents. This API performs a direct query on the OpenSearch database.

The second API ```/reviews/{count}/start_date/{start_date}/end_date/{end_date}/reviewer/{reviewer}/description/{description}``` is similar to the first except it takes in additional reviewer and description arguments. This API uses a Bedrock KB hybrid query type - filters using count, start_date, end_date, reviewers and semantic similarity using vectors.  

## Run

1. Install requirements

```bash
pip install -r requirements.txt
```

2. Step through the cells in main.ipynb

3. Interact using streamlit web app

Fill in agent id and alias in agent.py

```bash
streamlit run main.py
```