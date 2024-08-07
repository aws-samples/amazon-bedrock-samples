import { Construct } from 'constructs';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { join } from 'path';
import { Effect, ManagedPolicy, Policy, PolicyDocument, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { aws_lambda, Duration, CfnOutput } from 'aws-cdk-lib';
import { RDSDatabaseForAgentWithROC } from './rds-database-roc-construct';


// export class VacationAPILambdaStack extends Stack {
export class VacationAPILambdaSetup extends Construct {

    constructor(scope: Construct, id: string) {
        super(scope, id);


        const rdsDatabase = new RDSDatabaseForAgentWithROC(this, 'RDSDatabaseForAgentWithFD');
        const auroraClusterArn = rdsDatabase.AuroraClusterArn;
        const auroraDatbaseSecretArn = rdsDatabase.AuroraDatabaseSecretArn;

        // Define the Lambda function
        const vacationFunction = new NodejsFunction(this, 'VacationFunction', {
            entry: join(__dirname, '..', '..', 'lambda', '02-agent-with-return-of-control', 'assist-with-vacation-lambda.ts'),
            handler: 'handler',
            runtime: aws_lambda.Runtime.NODEJS_18_X,
            timeout: Duration.minutes(10),
            environment: {
                CLUSTER_ARN: auroraClusterArn,
                SECRET_ARN: auroraDatbaseSecretArn,
            },
        });

        // Allow the Lambda function to access the Aurora Serverless and be able to query the database
        const managedPolicies = [
            ManagedPolicy.fromAwsManagedPolicyName('AmazonRDSDataFullAccess'),
        ];

        // Attach the managed policies to the Lambda function's role
        managedPolicies.forEach(policy => {
            vacationFunction.role?.addManagedPolicy(policy);
        });

        // Allow the Lambda function to access the Aurora Serverless Secret Manager to get the database credentials
        const allowAccessSecretManagerPolicy = new PolicyDocument({
            statements: [
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['secretsmanager:GetSecretValue'],
                    resources: ['*']
                })
            ]
        });

        // Attach the custom policy to the Lambda function's role
        vacationFunction.role?.attachInlinePolicy(new Policy(this, 'AllowAccessSecretManagerPolicy', {
            document: allowAccessSecretManagerPolicy,
        }));

        // Define the API Gateway to trigger the Lambda function
        // API Gateway is used to expose the Lambda function as an HTTP endpoint
        const api = new apigateway.RestApi(this, 'VacationAPI', {
            restApiName: 'Vacation API',
            description: 'This service serves a Lambda function for managing employee vacation data.',
        });

        const lambdaIntegration = new apigateway.LambdaIntegration(vacationFunction);

        // Define the API Gateway resource
        const vacationResource = api.root.addResource('vacation');

        // Define the POST method with its request model
        const postMethod = vacationResource.addMethod('POST', lambdaIntegration, {
            requestModels: {
                'application/json': new apigateway.Model(this, 'PostRequestModel', {
                    restApi: api,
                    contentType: 'application/json',
                    schema: {
                        schema: apigateway.JsonSchemaVersion.DRAFT4,
                        type: apigateway.JsonSchemaType.OBJECT,
                        properties: {
                            func: { type: apigateway.JsonSchemaType.STRING },
                            parameters: {
                                type: apigateway.JsonSchemaType.ARRAY,
                                items: {
                                    type: apigateway.JsonSchemaType.OBJECT,
                                    properties: {
                                        name: { type: apigateway.JsonSchemaType.STRING },
                                        value: { type: apigateway.JsonSchemaType.STRING },
                                    },
                                    required: ['name', 'value'],
                                },
                            },
                        },
                        required: ['func', 'parameters'],
                    },
                }),
            },
        });

        // Define the GET method with its request model
        const getMethod = vacationResource.addMethod('GET', lambdaIntegration, {
            requestModels: {
                'application/json': new apigateway.Model(this, 'GetRequestModel', {
                    restApi: api,
                    contentType: 'application/json',
                    schema: {
                        schema: apigateway.JsonSchemaVersion.DRAFT4,
                        type: apigateway.JsonSchemaType.OBJECT,
                        properties: {
                            func: { type: apigateway.JsonSchemaType.STRING },
                            parameters: {
                                type: apigateway.JsonSchemaType.ARRAY,
                                items: {
                                    type: apigateway.JsonSchemaType.OBJECT,
                                    properties: {
                                        name: { type: apigateway.JsonSchemaType.STRING },
                                        value: { type: apigateway.JsonSchemaType.STRING },
                                    },
                                    required: ['name', 'value'],
                                },
                            },
                        },
                        required: ['func', 'parameters'],
                    },
                }),
            },
        });

        // Create an API key
        const apiKey = api.addApiKey('VacationApiKey');

        // Create a usage plan and associate the API key with it to enforce the usage limits
        const usagePlan = api.addUsagePlan('VacationUsagePlan', {
            name: 'Easy',
            throttle: {
                rateLimit: 10,
                burstLimit: 2,
            },
            quota: {
                limit: 10000,
                period: apigateway.Period.MONTH,
            },
        });

        usagePlan.addApiKey(apiKey);
        usagePlan.addApiStage({
            stage: api.deploymentStage,
            throttle: [
                {
                    method: postMethod,
                    throttle: {
                        rateLimit: 10,
                        burstLimit: 2,
                    },
                },
                {
                    method: getMethod,
                    throttle: {
                        rateLimit: 10,
                        burstLimit: 2,
                    },
                },
            ],
        });

        // Output the API endpoint
        new CfnOutput(this, 'APIEndpoint', {
            value: api.url ?? 'Something went wrong with the deploy',
        });
    }
}
