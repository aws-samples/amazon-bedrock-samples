"""
Create a custom dashboard in CloudWatch with
relevant metrics associated with Bedrock app.

Update Parameters (Line 22) based on details of your app, 
such as Lambda function name, Knowledge base ID, Model name

Note: the `InvocationSummary by User` component of
this dashboard assumes you have invocation logs
enabled under Bedrock settings. If you don't enable
invocation logs, you will see no data for this
component. Update loggroup name in line 268 to match 
the log group name where Bedrock invocation logs 
are being sent.
"""

import json
import boto3


# Parameters
region = "us-east-1"
lambda_name = "InvokeKnowledgeBase"
knowledge_base_name = "bedrock-sample-knowledge-base-111"
invoke_model_id = "anthropic.claude-instant-v1"
dashboard_name = "Contextual-Chatbot-Dashboard"


def knowledge_base_id_to_oss_collection(knowledge_base_id):
    bedrock_agent_client = boto3.client("bedrock-agent")
    response = bedrock_agent_client.get_knowledge_base(
        knowledgeBaseId=knowledge_base_id
    )
    collection_id = response["knowledgeBase"]["storageConfiguration"][
        "opensearchServerlessConfiguration"
    ]["collectionArn"].split("/")[-1]
    return collection_id


def knowledge_base_name_to_id(knowledge_base_name):
    bedrock_agent_client = boto3.client("bedrock-agent")
    response = bedrock_agent_client.list_knowledge_bases()
    for knowledge_base in response["knowledgeBaseSummaries"]:
        if knowledge_base["name"] == knowledge_base_name:
            return knowledge_base["knowledgeBaseId"]
    try:
        next_token = response["nextToken"]
    except Exception as e:
        next_token = None
    while next_token:
        response = bedrock_agent_client.list_knowledge_bases(nextToken=next_token)
        for knowledge_base in response["knowledgeBaseSummaries"]:
            if knowledge_base["name"] == knowledge_base_name:
                return knowledge_base["knowledgeBaseId"]
        try:
            next_token = response["NextToken"]
        except Exception as e:
            next_token = None
    return None


def generate_dashboard_json(region, knowledge_base_name, invoke_model_id):
    # Get account ID
    sts_client = boto3.client("sts")
    caller_identity = sts_client.get_caller_identity()
    account_id = caller_identity["Account"]

    # Get OpenSearch Serverless info
    knowledge_base_id = knowledge_base_name_to_id(knowledge_base_name)
    collection_id = knowledge_base_id_to_oss_collection(knowledge_base_id)
    oss_client = boto3.client("opensearchserverless")
    collection_name = oss_client.batch_get_collection(
        ids=[collection_id],
    )[
        "collectionDetails"
    ][0]["name"]

    # Embedding model ID
    bedrock_agent_client = boto3.client("bedrock-agent")
    response = bedrock_agent_client.get_knowledge_base(
        knowledgeBaseId=knowledge_base_id
    )
    embed_model_id = response["knowledgeBase"]["knowledgeBaseConfiguration"][
        "vectorKnowledgeBaseConfiguration"
    ]["embeddingModelArn"].split("/")[-1]

    dashboard_def = {
        "variables": [],
        "widgets": [
            {
                "height": 6,
                "width": 8,
                "y": 0,
                "x": 8,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/Bedrock",
                            "Invocations",
                            "ModelId",
                            f"arn:aws:bedrock:{region}::foundation-model/{invoke_model_id}",
                            {"region": region},
                        ],
                        [
                            "...",
                            f"arn:aws:bedrock:{region}::foundation-model/{embed_model_id}",
                            {"region": region},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": region,
                    "period": 60,
                    "stat": "Sum",
                    "yAxis": {"left": {"label": "Count", "showUnits": False}},
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 0,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/Bedrock",
                            "InvocationLatency",
                            "ModelId",
                            "ai21.j2-mid-v1",
                            {"region": region, "yAxis": "right", "visible": False},
                        ],
                        [
                            "...",
                            "anthropic.claude-v2",
                            {
                                "region": region,
                                "yAxis": "left",
                                "period": 60,
                                "visible": False,
                            },
                        ],
                        [
                            "...",
                            "stability.stable-diffusion-xl-v0",
                            {"region": region, "yAxis": "right", "visible": False},
                        ],
                        [
                            "...",
                            "ai21.j2-ultra-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "amazon.titan-image-generator-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "amazon.titan-text-express-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "anthropic.claude-instant-v1",
                            {
                                "region": region,
                                "yAxis": "left",
                                "period": 60,
                                "visible": False,
                            },
                        ],
                        [
                            "...",
                            "anthropic.claude-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "anthropic.claude-v2:1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            f"arn:aws:bedrock:{region}::foundation-model/{embed_model_id}",
                            {"region": region, "period": 60},
                        ],
                        [
                            "...",
                            f"arn:aws:bedrock:{region}::foundation-model/{invoke_model_id}",
                            {"region": region, "period": 60},
                        ],
                        [
                            "...",
                            "meta.llama2-13b-chat-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "meta.llama2-70b-chat-v1",
                            {"region": region, "visible": False},
                        ],
                        [
                            "...",
                            "stability.stable-diffusion-xl-v1",
                            {"region": region, "visible": False},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "period": 300,
                    "stat": "Average",
                    "yAxis": {"right": {"showUnits": False}},
                },
            },
            {
                "height": 6,
                "width": 12,
                "y": 6,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Bedrock", "InputTokenCount", {"region": region}],
                        [".", "OutputTokenCount", {"region": region}],
                    ],
                    "sparkline": False,
                    "view": "gauge",
                    "region": region,
                    "yAxis": {"left": {"min": 20, "max": 10000}},
                    "period": 60,
                    "stat": "Sum",
                    "annotations": {
                        "horizontal": [
                            {
                                "color": "#d62728",
                                "label": "Above forecasts",
                                "value": 7000,
                                "fill": "above",
                            },
                            {
                                "color": "#2ca02c",
                                "label": "Untitled annotation",
                                "value": 5000,
                                "fill": "below",
                            },
                            [
                                {
                                    "color": "#ff7f0e",
                                    "label": "Untitled annotation",
                                    "value": 5001,
                                },
                                {"value": 6999, "label": "Untitled annotation"},
                            ],
                        ]
                    },
                },
            },
            {
                "height": 6,
                "width": 12,
                "y": 6,
                "x": 12,
                "type": "log",
                "properties": {
                    "query": "SOURCE '/test/textGeneration/Bedrock' | fields @timestamp, identity.arn, input.inputTokenCount, output.outputTokenCount\n| stats sum(input.inputTokenCount) as totalInputTokens, sum(output.outputTokenCount) as totalOutputTokens, count(*) as invocationCount by identity.arn",
                    "region": region,
                    "stacked": False,
                    "title": "InvocationSummary by User",
                    "view": "table",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 12,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/AOSS",
                            "IndexingOCU",
                            "ClientId",
                            account_id,
                            {"region": region},
                        ],
                        [".", "SearchOCU", ".", ".", {"region": region}],
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": region,
                    "legend": {"position": "bottom"},
                    "title": "VectorDB - IndexingOCU, SearchOCU",
                    "period": 60,
                    "stat": "Average",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 12,
                "x": 8,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/AOSS",
                            "IndexingOCU",
                            "ClientId",
                            account_id,
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchOCU",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchableDocuments",
                            "CollectionName",
                            collection_name,
                            "CollectionId",
                            collection_id,
                            "ClientId",
                            account_id,
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchRequestRate",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"region": region, "period": 60},
                        ],
                        [
                            ".",
                            "SearchRequestErrors",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "2xx",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"region": region, "period": 60},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "legend": {"position": "bottom"},
                    "stat": "Average",
                    "period": 300,
                    "title": "VectorDB - 2xx, SearchRequestRate",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 12,
                "x": 16,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/AOSS",
                            "IndexingOCU",
                            "ClientId",
                            account_id,
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchOCU",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchableDocuments",
                            "CollectionName",
                            collection_name,
                            "CollectionId",
                            collection_id,
                            "ClientId",
                            account_id,
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchRequestRate",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchRequestErrors",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"region": region, "period": 60},
                        ],
                        [
                            ".",
                            "2xx",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "legend": {"position": "bottom"},
                    "stat": "Average",
                    "period": 300,
                    "title": "SearchRequestErrors",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 12,
                "x": 8,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/AOSS",
                            "IndexingOCU",
                            "ClientId",
                            account_id,
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchOCU",
                            ".",
                            ".",
                            {"visible": False, "region": region},
                        ],
                        [
                            ".",
                            "SearchRequestLatency",
                            "CollectionName",
                            collection_name,
                            "CollectionId",
                            collection_id,
                            "ClientId",
                            account_id,
                            {"region": region},
                        ],
                        [
                            ".",
                            "IngestionRequestLatency",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            ".",
                            {"region": region},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "legend": {"position": "bottom"},
                    "stat": "Average",
                    "period": 300,
                    "title": "RetrievalLatency",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 12,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Invocations", "FunctionName", lambda_name],
                        [".", "Errors", ".", "."],
                        [".", "Throttles", ".", "."],
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": region,
                    "title": "Lambda Performance",
                    "period": 60,
                    "stat": "Sum",
                },
            },
            {
                "height": 6,
                "width": 8,
                "y": 0,
                "x": 16,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/Bedrock",
                            "OutputTokenCount",
                            "ModelId",
                            f"arn:aws:bedrock:{region}::foundation-model/{embed_model_id}",
                            {"region": region},
                        ],
                        [
                            "AWS/Bedrock",
                            "OutputTokenCount",
                            "ModelId",
                            f"arn:aws:bedrock:{region}::foundation-model/{invoke_model_id}",
                            {"region": region},
                        ],
                        [
                            "AWS/Bedrock",
                            "InputTokenCount",
                            "ModelId",
                            f"arn:aws:bedrock:{region}::foundation-model/{invoke_model_id}",
                            {"region": region},
                        ],
                        [
                            "AWS/Bedrock",
                            "InputTokenCount",
                            "ModelId",
                            f"arn:aws:bedrock:{region}::foundation-model/{embed_model_id}",
                            {"region": region},
                        ],
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": region,
                    "title": "Token usage",
                    "period": 300,
                    "stat": "Average",
                },
            },
        ],
    }
    return json.dumps(dashboard_def)


def create_dashboard(dashboard_name, dashboard_json):
    # Create log group
    try:
        logs_client = boto3.client("logs")
        logs_client.create_log_group(logGroupName="textGeneration/Bedrock")
    except Exception as e:
        # Log group already exists
        pass

    # Create custom dashboard
    cw_client = boto3.client("cloudwatch")
    cw_client.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=dashboard_json,
    )



# Create custom dashboard for your Bedrock app
dashboard_json = generate_dashboard_json(region, knowledge_base_name, invoke_model_id)
create_dashboard(dashboard_name, dashboard_json)
