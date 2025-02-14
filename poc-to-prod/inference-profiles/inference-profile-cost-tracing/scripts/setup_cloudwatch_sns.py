import boto3
import json
import os
from scripts.utils import get_s3_file_content

os.environ['AWS_PROFILE'] = 'cost-tracing'


def main():
    # Load configuration
    bucket_name = 'inference-cost-tracing'
    config_file = 'config/config.json'

    config_file = get_s3_file_content(bucket_name, config_file)
    config = json.loads(config_file)

    region = config['aws_region']

    dashboard_name = config['dashboard_name']
    cost_threshold = config['cost_alarm_threshold']
    tokens_per_min_threshold = config['token_alarm_threshold']
    requests_per_min_threshold = config['request_alarm_threshold']

    cloudwatch_client = boto3.client('cloudwatch', region_name=region)
    sns_client = boto3.client('sns', region_name=region)

    # Create SNS topic
    sns_response = sns_client.create_topic(Name=config['sns_topic_name'])
    topic_arn = sns_response['TopicArn']

    # Subscribe email to SNS topic
    sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=config['sns_email']
    )
    print('SNS topic created and email subscription added.')

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------
    # Variable for selecting an InferenceProfile
    variables = [
        {
            "type": "property",
            "property": "InferenceProfile",
            "inputType": "select",
            "id": "profileVariable",
            "label": "Inference Profile",
            "visible": True,
            "search": "{BedrockInvocationTracing,InferenceProfile} MetricName=\"InputTokens\"",
            "populateFrom": "InferenceProfile",
            "defaultValue": "__FIRST"
        }
    ]

    # --------------------------------------------------------
    # Original Widgets (Tokens, Costs, TPM, RPM)
    # --------------------------------------------------------
    tokens_widget = {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InputTokens", "InferenceProfile", "${profileVariable}",
                 {"stat": "Sum", "label": "Input Tokens"}],
                [".", "OutputTokens", ".", ".", {"stat": "Sum", "label": "Output Tokens"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Token Counts (Variable Profile)",
            "period": 300
        }
    }

    cost_widget = {
        "type": "metric",
        "x": 12,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InputTokensCost", "InferenceProfile", "${profileVariable}",
                 {"stat": "Sum", "label": "Input Token Cost ($)"}],
                [".", "OutputTokensCost", ".", ".", {"stat": "Sum", "label": "Output Token Cost ($)"}],
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Token Costs (Variable Profile)",
            "period": 300
        }
    }

    tokens_per_min_widget = {
        "type": "metric",
        "x": 0,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InputTokens", "InferenceProfile", "${profileVariable}",
                 {"period": 60, "stat": "Sum", "label": "Input (1m)", "id": "it"}],
                ["BedrockInvocationTracing", "OutputTokens", "InferenceProfile", "${profileVariable}",
                 {"period": 60, "stat": "Sum", "label": "Output (1m)", "id": "ot"}],
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Tokens per Minute (Variable Profile)",
            "period": 60
        }
    }

    requests_per_min_widget = {
        "type": "metric",
        "x": 12,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InvocationSuccess", "InferenceProfile", "${profileVariable}",
                 {"period": 60, "stat": "Sum", "label": "Success (1m)", "id": "is"}],
                ["BedrockInvocationTracing", "InvocationFailure", "InferenceProfile", "${profileVariable}",
                 {"period": 60, "stat": "Sum", "label": "Failure (1m)", "id": "if"}],
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Requests per Minute (Variable Profile)",
            "period": 60
        }
    }

    # --------------------------------------------------------
    # Daily Summary Widgets (split out)
    # --------------------------------------------------------

    # 1) Daily Tokens Widget (Input/Output)
    daily_tokens_widget = {
        "type": "metric",
        "x": 0,
        "y": 12,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InputTokens", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Input Tokens"}],
                ["BedrockInvocationTracing", "OutputTokens", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Output Tokens"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Daily Tokens (Variable Profile)",
            "period": 86400
        }
    }

    # 2) Daily Cost Widget (Input/Output)
    daily_cost_widget = {
        "type": "metric",
        "x": 8,
        "y": 12,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InputTokensCost", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Input Token Cost ($)"}],
                ["BedrockInvocationTracing", "OutputTokensCost", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Output Token Cost ($)"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Daily Costs (Variable Profile)",
            "period": 86400
        }
    }

    # 3) Daily Requests Widget (Success/Failure)
    daily_requests_widget = {
        "type": "metric",
        "x": 16,
        "y": 12,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                ["BedrockInvocationTracing", "InvocationSuccess", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Successful Requests"}],
                ["BedrockInvocationTracing", "InvocationFailure", "InferenceProfile", "${profileVariable}",
                 {"period": 86400, "stat": "Sum", "label": "Daily Failed Requests"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Daily Requests (Variable Profile)",
            "period": 86400
        }
    }

    # --------------------------------------------------------
    # All Inference Profiles Bar Graphs
    # --------------------------------------------------------
    # 1) All Inference Profiles Cost Bar Graph
    # Using SEARCH expressions to get InputTokensCost and OutputTokensCost across all profiles.
    all_profiles_cost_widget = {
        "type": "metric",
        "x": 0,
        "y": 18,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"InputTokensCost\"','Sum',300)",
                     "id": "itc", "label": "Input Tokens Cost", "color": "#FFA500"}],
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"OutputTokensCost\"','Sum',300)",
                     "id": "otc", "label": "Output Tokens Cost", "color": "#00FF00"}],
            ],
            "view": "bar",
            "stacked": True,
            "region": region,
            "title": "All Inference Profiles Cost (bar)",
            "period": 300
        }
    }

    # 2) All Inference Profiles Requests per Minute (bar)
    all_profiles_rpm_widget = {
        "type": "metric",
        "x": 8,
        "y": 18,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"InvocationSuccess\"','Sum',60)",
                     "id": "is", "label": "Success", "color": "#800080"}],
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"InvocationFailure\"','Sum',60)",
                     "id": "if", "label": "Failure", "color": "#808080"}],
            ],
            "view": "bar",
            "stacked": True,
            "region": region,
            "title": "All Inference Profiles Requests/Min (bar)",
            "period": 60
        }
    }

    # 3) All Inference Profiles Tokens per Minute (bar)
    all_profiles_tpm_widget = {
        "type": "metric",
        "x": 16,
        "y": 18,
        "width": 8,
        "height": 6,
        "properties": {
            "metrics": [
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"InputTokens\"','Sum',60)",
                     "id": "it", "label": "Input", "color": "#FF0000"}],
                [{
                     "expression": "SEARCH('{BedrockInvocationTracing,InferenceProfile} MetricName=\"OutputTokens\"','Sum',60)",
                     "id": "ot", "label": "Output", "color": "#0000FF"}],
            ],
            "view": "bar",
            "stacked": True,
            "region": region,
            "title": "All Inference Profiles Tokens/Min (bar)",
            "period": 60
        }
    }

    dashboard_body = json.dumps({
        "variables": variables,
        "widgets": [
            tokens_widget,
            cost_widget,
            tokens_per_min_widget,
            requests_per_min_widget,
            daily_tokens_widget,
            daily_cost_widget,
            daily_requests_widget,
            all_profiles_cost_widget,
            all_profiles_rpm_widget,
            all_profiles_tpm_widget
        ]
    })

    cloudwatch_client.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=dashboard_body
    )
    print('CloudWatch dashboard updated with requested widgets.')

    cloudwatch_client.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=dashboard_body
    )
    print('CloudWatch dashboard updated with variables and daily summary widget.')
    profiles = config['profiles']
    for profile in profiles:
        profile_name = profile['name']
        cloudwatch_client.put_metric_alarm(
            AlarmName=f'BedrockTokenCostAlarm-{profile_name}',
            AlarmDescription=f'Alarm when total token cost for {profile_name} exceeds ${cost_threshold} in 5 minutes',
            ActionsEnabled=True,
            AlarmActions=[topic_arn],
            Metrics=[
                {
                    'Id': 'itc',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'InputTokensCost',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 300,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'otc',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'OutputTokensCost',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 300,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'totalCost',
                    'Expression': 'itc + otc',
                    'ReturnData': True
                }
            ],
            ComparisonOperator='GreaterThanOrEqualToThreshold',
            Threshold=cost_threshold,
            EvaluationPeriods=1,
            TreatMissingData='notBreaching'
        )
        print('Cost alarm created/updated.')

        # Tokens Per Minute Alarm:
        # If total tokens per minute exceed a threshold
        cloudwatch_client.put_metric_alarm(
            AlarmName=f'BedrockTokensPerMinuteAlarm-{profile_name}',
            AlarmDescription=f'Alarm when tokens per minute for {profile_name} exceed {tokens_per_min_threshold}',
            ActionsEnabled=True,
            AlarmActions=[topic_arn],
            Metrics=[
                {
                    'Id': 'it',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'InputTokens',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'ot',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'OutputTokens',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'totalTokensPerMin',
                    'Expression': 'it + ot',
                    'ReturnData': True
                }
            ],
            ComparisonOperator='GreaterThanOrEqualToThreshold',
            Threshold=tokens_per_min_threshold,
            EvaluationPeriods=1,
            TreatMissingData='notBreaching'
        )
        print('Tokens per minute alarm created/updated.')

        # Requests Per Minute Alarm:
        # If requests per minute exceed a threshold
        cloudwatch_client.put_metric_alarm(
            AlarmName=f'BedrockRequestsPerMinuteAlarm-{profile_name}',
            AlarmDescription=f'Alarm when requests per minute for {profile_name} exceed {requests_per_min_threshold}',
            ActionsEnabled=True,
            AlarmActions=[topic_arn],
            Metrics=[
                {
                    'Id': 'is',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'InvocationSuccess',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'if',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'BedrockInvocationTracing',
                            'MetricName': 'InvocationFailure',
                            'Dimensions': [
                    {'Name': 'InferenceProfile', 'Value': profile_name}
                ]
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False
                },
                {
                    'Id': 'requestsPerMin',
                    'Expression': 'is + if',
                    'ReturnData': True
                }
            ],
            ComparisonOperator='GreaterThanOrEqualToThreshold',
            Threshold=requests_per_min_threshold,
            EvaluationPeriods=1,
            TreatMissingData='notBreaching'
        )
        print('Requests per minute alarm created/updated.')


if __name__ == '__main__':
    main()