import boto3
from datetime import datetime, timedelta
import json
from typing import Dict, Any


ce = boto3.client('ce')


def get_savings_plan_recommendations(savings_plan_type: str, account_scope='PAYER', lookback_period='SEVEN_DAYS', term='ONE_YEAR', payment_option='NO_UPFRONT') -> Dict[str, Any]:
    try:
        response = ce.get_savings_plans_purchase_recommendation(
            AccountScope=account_scope,
            LookbackPeriodInDays=lookback_period,
            TermInYears=term,
            PaymentOption=payment_option,
            SavingsPlansType=savings_plan_type
        )
        result = {
            "SavingsPlansPurchaseRecommendation" : response["SavingsPlansPurchaseRecommendation"]}

        return result
    except Exception as e:
        print(f"An error occurred in get_savings_plan_recommendations: {e}")
        return {'error': str(e)}


def get_savings_plan_recommendation_details(recommendation_arn: str) -> Dict[str, Any]:
    try:
        response = ce.get_savings_plans_purchase_recommendation_details(
            RecommendationArn=recommendation_arn
        )
        result = {
            "RecommendationDetailData" : response["RecommendationDetailData"]}
        return result
    except Exception as e:
        print(f"An error occurred in get_savings_plan_recommendation_details: {e}")
        return {'error': str(e)}


def get_savings_plan_utilization(billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    try:
        response = ce.get_savings_plans_utilization(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            }
        )
        return response
    except Exception as e:
        print(f"An error occurred in get_savings_plan_utilization: {e}")
        return {'error': str(e)}


def get_savings_plan_utilization_details(billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    try:
        response = ce.get_savings_plans_utilization_details(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            }
        )
        return response
    except Exception as e:
        print(f"An error occurred in get_savings_plan_utilization_details: {e}")
        return {'error': str(e)}


def get_savings_plans_coverage(billing_period_start: str, billing_period_end: str, granularity='MONTHLY') -> Dict[str, Any]:
    try:
        response = ce.get_savings_plans_coverage(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            },
            Granularity=granularity
        )
        result = {
            "SavingsPlansCoverages" : response["SavingsPlansCoverages"]}
        return result
    except Exception as e:
        print(f"An error occurred in get_savings_plans_coverage: {e}")
        return {'error': str(e)}


def lambda_handler(event, context):
    print(f'Processing Event received from Bedrock Agent')
    response_code = 200
    action = event.get('actionGroup')
    api_path = event.get('apiPath')

    try:
        if api_path == '/get_savings_plan_recommendations':
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            account_scope = parameters.get('account_scope', 'PAYER')
            lookback_period = parameters.get('lookback_period', 'THIRTY_DAYS')
            term = parameters.get('term', 'ONE_YEAR')
            savins_plan_type = parameters.get('savings_plan_type', 'COMPUTE_SP')
            payment_option = parameters.get('payment_option', 'NO_UPFRONT')
            body = get_savings_plan_recommendations(savins_plan_type, account_scope, lookback_period, term, payment_option)
        elif api_path == '/get_savings_plan_recommendation_details':
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            recommendation_arn = parameters.get('recommendation_arn')
            body = get_savings_plan_recommendation_details(recommendation_arn)
        elif api_path == '/get_savings_plan_utilization':
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            billing_period_start = parameters.get('billing_period_start')
            billing_period_end = parameters.get('billing_period_end')
            billing_period_end = datetime.strptime(
                billing_period_end, '%Y-%m-%d') + timedelta(days=1)
            billing_period_end = billing_period_end.strftime('%Y-%m-%d')
            body = get_savings_plan_utilization(billing_period_start, billing_period_end)
        elif api_path == '/get_savings_plan_utilization_details':
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            billing_period_start = parameters.get('billing_period_start')
            billing_period_end = parameters.get('billing_period_end')
            billing_period_end = datetime.strptime(
                billing_period_end, '%Y-%m-%d') + timedelta(days=1)
            billing_period_end = billing_period_end.strftime('%Y-%m-%d')
            body = get_savings_plan_utilization_details(billing_period_start, billing_period_end)
        elif api_path == '/get_savings_plans_coverage':
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            billing_period_start = parameters.get('billing_period_start')
            billing_period_end = parameters.get('billing_period_end')
            billing_period_end = datetime.strptime(
                billing_period_end, '%Y-%m-%d') + timedelta(days=1)
            billing_period_end = billing_period_end.strftime('%Y-%m-%d')
            granularity = parameters.get('granularity', 'MONTHLY')
            body = get_savings_plans_coverage(billing_period_start, billing_period_end, granularity)
        else:
            body = {"error": f"{action}::{api_path} is not a valid API, try another one."}
            response_code = 400
    except Exception as e:
        body = {'error': str(e)}
        response_code = 500

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