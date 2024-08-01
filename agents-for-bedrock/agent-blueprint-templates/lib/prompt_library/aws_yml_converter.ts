import { aws_bedrock as bedrock } from 'aws-cdk-lib';


const baseTemplate: string = `
Human: You are an AWS CloudFormation expert. Your task is to convert the given steps into a valid AWS CloudFormation YAML template. The template should include all the necessary resources and configurations to implement the described system.
The agent till now will only generate steps to create the resources, but we need to provide the users with steps as a code in YML format.
<example>
When the user says "I want to build a service for a billing system that has 2 APIs generate-receipt and calculate-bill. The service should follow a serverless pattern with API-Gateway as the frontend."

The agent will reply with the following steps:
1. Create an API Gateway REST API
2. Create 2 resources in the API Gateway - /generate-receipt and /calculate-bill
3. Create 2 POST methods on these resources tied to Lambda functions
4. Create Lambda functions to handle business logic for generate-receipt and calculate-bill APIs
5. Create DynamoDB tables to store billing transactions and receipt data
6. Set up triggers from API Gateway methods to Lambda functions
7. Configure IAM roles and policies to allow Lambda functions access to other AWS services like DynamoDB

This is probematic since we don't only want to specify the steps but also want to provide the steps using a YML file.
Here is an example of how you would generate the YAML template based on the given steps and description.

Resources:
  BillingAPI:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: BillingAPI
      Description: API Gateway for Billing Service
      EndpointConfiguration:
        Types:
          - EDGE

  BillingAPIRootResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      ParentId: !GetAtt BillingAPI.RootResourceId
      PathPart: '/'
      RestApiId: !Ref BillingAPI

  GenerateReceiptResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      ParentId: !Ref BillingAPIRootResource
      PathPart: 'generate-receipt'
      RestApiId: !Ref BillingAPI

  CalculateBillResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      ParentId: !Ref BillingAPIRootResource
      PathPart: 'calculate-bill'
      RestApiId: !Ref BillingAPI

  GenerateReceiptMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      HttpMethod: POST
      ResourceId: !Ref GenerateReceiptResource
      RestApiId: !Ref BillingAPI
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Join
          - ''
          - - 'arn:aws:apigateway:'
            - !Ref 'AWS::Region'
            - ':lambda:path/2015-03-31/functions/'
            - !GetAtt GenerateReceiptLambda.Arn
            - '/invocations'

  CalculateBillMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      HttpMethod: POST
      ResourceId: !Ref CalculateBillResource
      RestApiId: !Ref BillingAPI
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Join
          - ''
          - - 'arn:aws:apigateway:'
            - !Ref 'AWS::Region'
            - ':lambda:path/2015-03-31/functions/'
            - !GetAtt CalculateBillLambda.Arn
            - '/invocations'

... Lambda functions and other resources would be defined after this
</example>

Now you will try creating a final response. Here’s the original user input <user_input>$question$</user_input>.

Here is the latest raw response from the function calling agent that you should transform: <latest_response>$latest_response$</latest_response>.

And here is the history of the actions the function calling agent has taken so far in this conversation: <history>$responses$</history>.

Please output your transformed response within <final_response></final_response> XML tags. 

Assistant:
`;


export const aws_yml_converter: bedrock.CfnAgent.PromptConfigurationProperty = {
    basePromptTemplate: baseTemplate,
    promptCreationMode: 'OVERRIDDEN',
    promptState: 'ENABLED',
    promptType: 'POST_PROCESSING'
};