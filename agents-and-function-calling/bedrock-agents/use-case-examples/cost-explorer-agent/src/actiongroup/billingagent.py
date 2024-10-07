import re
import boto3
from datetime import datetime, timedelta
import json
from typing import Dict, Any
import pandas as pd

ce = boto3.client('ce')


def get_today_date() -> Dict[str, str]:
    """Gets the current date in YYYY-MM-DD format and the current month in YYYY-MM format."""
    return {
        'today_date': datetime.now().strftime('%Y-%m-%d'),
        'current_month': datetime.now().strftime('%Y-%m')
    }


def get_dimension_values(key: str, billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Get available values for a specific dimension."""
    try:
        response = ce.get_dimension_values(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            },
            Dimension=key.upper()
        )
        dimension_values = response['DimensionValues']
        values = [value['Value'] for value in dimension_values]
        return {'dimension': key.upper(), 'values': values}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {'error': str(e)}


def get_tag_values(tag_key: str, billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Get available values for a specific tag key."""
    try:
        response = ce.get_tags(
            TimePeriod={'Start': billing_period_start,
                        'End': billing_period_end},
            TagKey=tag_key
        )
        tag_values = response['Tags']
        return {'tag_key': tag_key, 'values': tag_values}
    except Exception as e:
        print(f"An error in tag values occurred: {e}")
        return {'error': str(e)}


def initial_json_validation(json_string):
    """
    Validate JSON string to ensure a logical operator is present if there are multiple expressions.
    """
    stripped_json = re.sub(r'\s+', '', json_string)

    # Look for multiple expressions
    multiple_expressions_pattern = re.compile(
        r'\"(Dimensions|Tags|CostCategories)\":\{')
    matches = multiple_expressions_pattern.findall(stripped_json)

    if len(matches) > 1:
        # Check for logical operators
        if not any(op in stripped_json for op in ['"And"', '"Or"', '"Not"']):
            return {'error': 'Multiple expressions found in the filter but no logical operator (And, Or, Not) is present.'}

    return json_string


def validate_expression(expression: Dict[str, Any], billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Recursively validate the filter expression."""
    if 'Dimensions' in expression:
        dimension = expression['Dimensions']
        if 'Key' not in dimension or 'Values' not in dimension or 'MatchOptions' not in dimension:
            return {'error': 'Dimensions filter must include "Key", "Values", and "MatchOptions".'}

        dimension_key = dimension['Key']
        dimension_values = dimension['Values']
        valid_values_response = get_dimension_values(
            dimension_key, billing_period_start, billing_period_end)
        if 'error' in valid_values_response:
            return {'error': valid_values_response['error']}
        valid_values = valid_values_response['values']
        for value in dimension_values:
            if value not in valid_values:
                return {'error': f"Invalid value '{value}' for dimension '{dimension_key}'. Valid values are: {valid_values}"}

    if 'Tags' in expression:
        tag = expression['Tags']
        if 'Key' not in tag or 'Values' not in tag or 'MatchOptions' not in tag:
            return {'error': 'Tags filter must include "Key", "Values", and "MatchOptions".'}

        tag_key = tag['Key']
        tag_values = tag['Values']
        valid_tag_values_response = get_tag_values(
            tag_key, billing_period_start, billing_period_end)
        if 'error' in valid_tag_values_response:
            return {'error': valid_tag_values_response['error']}
        valid_tag_values = valid_tag_values_response['values']
        for value in tag_values:
            if value not in valid_tag_values:
                return {'error': f"Invalid value '{value}' for tag '{tag_key}'. Valid values are: {valid_tag_values}"}

    if 'CostCategories' in expression:
        cost_category = expression['CostCategories']
        if 'Key' not in cost_category or 'Values' not in cost_category or 'MatchOptions' not in cost_category:
            return {'error': 'CostCategories filter must include "Key", "Values", and "MatchOptions".'}

    logical_operators = ['And', 'Or', 'Not']
    logical_count = sum(1 for op in logical_operators if op in expression)

    if logical_count > 1:
        return {'error': 'Only one logical operator (And, Or, Not) is allowed per expression in filter parameter.'}

    if logical_count == 0 and len(expression) > 1:
        return {'error': 'Filter parameter with multiple expressions require a logical operator (And, Or, Not).'}

    if 'And' in expression:
        if not isinstance(expression['And'], list):
            return {'error': 'And expression must be a list of expressions.'}
        for sub_expression in expression['And']:
            result = validate_expression(
                sub_expression, billing_period_start, billing_period_end)
            if 'error' in result:
                return result

    if 'Or' in expression:
        if not isinstance(expression['Or'], list):
            return {'error': 'Or expression must be a list of expressions.'}
        for sub_expression in expression['Or']:
            result = validate_expression(
                sub_expression, billing_period_start, billing_period_end)
            if 'error' in result:
                return result

    if 'Not' in expression:
        if not isinstance(expression['Not'], dict):
            return {'error': 'Not expression must be a single expression.'}
        result = validate_expression(
            expression['Not'], billing_period_start, billing_period_end)
        if 'error' in result:
            return result

    if not any(k in expression for k in ['Dimensions', 'Tags', 'CostCategories', 'And', 'Or', 'Not']):
        return {'error': 'Filter Expression must include at least one of the following keys: "Dimensions", "Tags", "CostCategories", "And", "Or", "Not".'}

    return {}


def generate_cost_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a cost report based on the provided parameters."""
    granularity = params.get('granularity', 'MONTHLY').upper()
    billing_period_start = params.get('billing_period_start')
    billing_period_end = params.get('billing_period_end')
    billing_period_end = (datetime.strptime(
        billing_period_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    metrics = params.get('metric', 'UnblendedCost')

    filter_criteria = params.get('filter', None)

    # Handle empty filter cases
    if filter_criteria in [None, "", "{}"]:
        filter_criteria = None
    else:
        try:
            initial_json_validation_result = initial_json_validation(
                filter_criteria)

            if 'error' in initial_json_validation_result:
                return initial_json_validation_result
            else:
                filter_criteria = json.loads(filter_criteria)
        except json.JSONDecodeError as e:
            return {'error': f'Invalid filter format: {str(e)}'}

        validation_result = validate_expression(
            filter_criteria, billing_period_start, billing_period_end)
        if 'error' in validation_result:
            return validation_result

    group_by = params.get('group_by', '{}')
    try:
        group_by = json.loads(group_by)
    except json.JSONDecodeError as e:
        return {'error': f'Invalid group_by format: {str(e)}'}

    if not isinstance(group_by, dict) or 'Type' not in group_by or 'Key' not in group_by:
        return {'error': 'group_by must be a dictionary with "Type" and "Key" keys.'}
    if group_by['Type'].upper() not in ['DIMENSION', 'TAG', 'COST_CATEGORY']:
        return {'error': 'Invalid group Type. Valid types are DIMENSION, TAG, and COST_CATEGORY.'}

    common_params = {
        'TimePeriod': {
            'Start': billing_period_start,
            'End': billing_period_end
        },
        'Granularity': granularity,
        'GroupBy': [{'Type': group_by['Type'].upper(), 'Key': group_by['Key']}],
        'Metrics': [metrics]
    }

    if filter_criteria:
        common_params['Filter'] = filter_criteria

    grouped_costs = {}
    next_token = None
    while True:
        if next_token:
            common_params['NextPageToken'] = next_token
        try:
            response = ce.get_cost_and_usage(**common_params)
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'error': str(e)}

        for result_by_time in response['ResultsByTime']:
            date = result_by_time['TimePeriod']['Start']
            for group in result_by_time['Groups']:
                group_key = group['Keys'][0]
                if metrics == 'UsageQuantity':
                    unit = group['Metrics'][metrics]['Unit']
                    amount = float(group['Metrics'][metrics]['Amount'])
                    grouped_costs.setdefault(date, {}).update(
                        {group_key: (amount, unit)})
                else:
                    cost = float(group['Metrics'][metrics]['Amount'])
                    grouped_costs.setdefault(
                        date, {}).update({group_key: cost})

        next_token = response.get('NextPageToken')
        if not next_token:
            break

    if metrics == 'UsageQuantity':
        # Prepare DataFrame to include usage with units
        usage_df = pd.DataFrame({(k, 'Amount'): {
                                k1: v1[0] for k1, v1 in v.items()} for k, v in grouped_costs.items()})
        units_df = pd.DataFrame(
            {(k, 'Unit'): {k1: v1[1] for k1, v1 in v.items()} for k, v in grouped_costs.items()})
        df = pd.concat([usage_df, units_df], axis=1)
    else:
        df = pd.DataFrame.from_dict(grouped_costs).round(2)
        df['Service total'] = df.sum(axis=1).round(2)
        df.loc['Total Costs'] = df.sum().round(2)
        df = df.sort_values(by='Service total', ascending=False)

    result = {'GroupedCosts': df.to_dict()}

    def stringify_keys(d):
        if isinstance(d, dict):
            return {str(k): stringify_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [stringify_keys(i) for i in d]
        else:
            return d

    # Convert the keys to strings for the entire result dictionary
    result = stringify_keys(result)

    if len(json.dumps(result)) > 25000:
        if metrics == 'UsageQuantity':
            df = usage_df[['Amount']]
        else:
            df = df[['Service total']]
        billing_period_end = (datetime.strptime(
            billing_period_end, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        result = {
            'warning': f'Due to the size of the response body exceeding 25KB, only the aggregated service total costs for the specified billing period ({billing_period_start} through {billing_period_end}) are provided. If you require detailed spending information, please adjust the filter or billing period and retry your request.',
            'GroupedCosts': stringify_keys(df.to_dict())
        }
        return result
    return result


def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    print(f'Processing Event received from Bedrock Agent')
    response_code = 200
    action = event['actionGroup']
    api_path = event['apiPath']

    if api_path == '/get_cost_and_usage':
        try:
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            body = generate_cost_report(parameters)
        except Exception as e:
            body = {'error': str(e)}
            response_code = 500
    elif api_path == '/get-dimension-values':
        try:
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            billing_period_start = parameters.get('billing_period_start')
            billing_period_end = (datetime.strptime(parameters.get(
                'billing_period_end'), '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            key = parameters.get('dimension_key', 'SERVICE')
            body = get_dimension_values(
                key, billing_period_start, billing_period_end)
        except Exception as e:
            body = {'error': str(e)}
            response_code = 500
    elif api_path == '/get-date':
        try:
            body = get_today_date()
        except Exception as e:
            body = {'error': str(e)}
            response_code = 500
    else:
        body = {"error": f"{action}::{
            api_path} is not a valid API, try another one."}
        response_code = 400

    if len(json.dumps(body)) > 25000:
        body = {
            "error": "The response size is larger than the agent can support. Please update the filter or billing period and try again."
        }
        response_code = 400
        print(f"The response is larger than the agent can support. Please update the filter or billing period and try again.")

    response_body = {'application/json': {'body': json.dumps(body)}}
    print(f'Response sent to Bedrock Agent')

    action_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action,
            "apiPath": api_path,
            "httpMethod": event['httpMethod'],
            "httpStatusCode": response_code,
            "responseBody": response_body
        }
    }

    return action_response
