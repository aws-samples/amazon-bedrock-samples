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

### Sample prompts and responses

1. Trigger direct query on OpenSearch

Prompt

```Give me the last 2 reviews```

Response

```text
Based on the provided date range of 1577808000000.0 to 1609430400000.0, the last 2 reviews are:

"I really like these ear swabs. First they come in a large, handy box and are easy to store (will last a long time). Second, they are all organic and good for the environment. Third, they are strong and don't fall apart very easily. I highly recommend these over Q-Tips (which I have used for years)." with a rating of 5.0 and a timestamp of 1596473351088.

"Super cute and great value!" with a rating of 5.0 and a timestamp of 1585211251700.
```

2. Trigger knowledge base retrieval API

Prompt

```give me the last review on hair spray from jokic```

Response

```text
Based on the provided date range of 1577808000000.0 to 1609430400000.0, and the search for the last review on hair spray from jokic, the review is:

"Last summer I decided to grow out my bangs after having them for all of my adult life. I hadn't used much hairspray since the eighties and into the nineties, but I found that I needed to spray my former bangs in order to help train them to their new position. This is a huge bottle of hair spray. It has a standard hair spray smell. It gives a nice mist. It doesn't leave my hair crunchy. It's a flexible hold so my hair moves and looks natural. So far I am pleased with it." with a rating of 4.0 and a timestamp of 1579351461183.
```