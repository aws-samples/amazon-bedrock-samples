import boto3
import json

client = boto3.client('cloudwatch')

region = "us-west-2"

dashboard_body={
    "variables": [],
    "widgets": [
        {
            "height": 6,
            "width": 6,
            "y": 0,
            "x": 6,
            "type": "metric",
            "properties": {
                "metrics": [
                    [ "AWS/Bedrock", "Invocations", { "region": region } ]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": region,
                "title": "Invocation Count",
                "period": 60,
                "stat": "Sum"
            }
        },
        {
            "height": 6,
            "width": 6,
            "y": 6,
            "x": 6,
            "type": "metric",
            "properties": {
                "metrics": [
                    [ "AWS/Bedrock", "InvocationLatency", { "region": region } ]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": region,
                "period": 60,
                "stat": "Average",
                "title": "Invocation Latency"
            }
        },
        {
            "height": 6,
            "width": 6,
            "y": 12,
            "x": 0,
            "type": "metric",
            "properties": {
                "view": "timeSeries",
                "stacked": False,
                "metrics": [
                    [ "AWS/Bedrock", "InvocationClientErrors" ]
                ],
                "region": region,
                "title": "Invocation Error Count"
            }
        },
        {
            "height": 6,
            "width": 6,
            "y": 6,
            "x": 0,
            "type": "metric",
            "properties": {
                "metrics": [
                    [ { "expression": "AVG(METRICS())", "label": "Expression1", "id": "e1", "visible": False, "region": region, "period": 60 } ],
                    [ "AWS/Bedrock", "Invocations", { "id": "m1", "region": region } ]
                ],
                "view": "gauge",
                "region": region,
                "stat": "Average",
                "period": 60,
                "yAxis": {
                    "left": {
                        "min": 0,
                        "max": 100000
                    }
                },
                "liveData": True,
                "title": "Invocations Per Minute"
            }
        },
        {
            "height": 6,
            "width": 6,
            "y": 0,
            "x": 0,
            "type": "metric",
            "properties": {
                "metrics": [
                    [ "AWS/Bedrock", "InputTokenCount", { "region": region } ],
                    [ ".", "OutputTokenCount", { "region": region } ]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": region,
                "title": "Token Counts",
                "period": 60,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 6,
            "y": 12,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Bedrock", "OutputImageCount", { "region": region } ]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": region,
                "title": "Output Image Count",
                "period": 60,
                "stat": "Average"
            }
        }
    ]
}

print(json.dumps(dashboard_body))

response = client.put_dashboard(
    DashboardName="AmazonBedrockDashboard",
    DashboardBody=json.dumps(dashboard_body)
)
