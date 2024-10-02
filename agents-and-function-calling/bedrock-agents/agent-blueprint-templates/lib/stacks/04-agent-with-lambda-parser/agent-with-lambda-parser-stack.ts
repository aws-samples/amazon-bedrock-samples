import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { BedrockAgentBlueprintsConstruct, AgentDefinitionBuilder, AgentActionGroup, PromptConfig_Override, PromptStateConfig, PromptType} from '@aws/agents-and-function-calling-for-amazon-bedrock-blueprints';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { join } from 'path';
import { CustomResource, Duration } from 'aws-cdk-lib';
import { Effect, ManagedPolicy, PolicyDocument, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Provider } from 'aws-cdk-lib/custom-resources';
import { RDSDatabaseForAgentWithLP } from '../04-agent-with-lambda-parser/rds-database-lp-construct';
import { customPreprocessingPrompt, customPostProcessingPrompt } from '../../prompt_library/prompts';
import { readFileSync } from 'fs';

export class AgentWithCustomLambdaParserStack extends Stack {
    constructor(scope: Construct, id: string, props?: StackProps) {
        super(scope, id, props);

        const rdsDatabase = new RDSDatabaseForAgentWithLP(this, 'RDSDatabaseForAgentWithLP');
        const auroraClusterArn = rdsDatabase.AuroraClusterArn;
        const auroraDatbaseSecretArn = rdsDatabase.AuroraDatabaseSecretArn;

        const managedPolicies = [
            ManagedPolicy.fromAwsManagedPolicyName('AmazonRDSDataFullAccess'),
        ];

        const allowAccessSecretManagerPolicy = new PolicyDocument({
            statements: [
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['secretsmanager:GetSecretValue'],
                    resources: ['*']
                })
            ]
        });

        const { customParserFunction } = this.createCustomParserResource();

        customParserFunction.addPermission('AllowBedrockToInvokeFunction', {
            principal: new ServicePrincipal('bedrock.amazonaws.com'),
            action: 'lambda:InvokeFunction',
        
        });

        const agentDef = new AgentDefinitionBuilder(this, 'HRAssistantAgent', {})
            .withAgentName('hr-assistant-agent-with-custom-parser')  
            .withInstruction(
                'As an HR agent, your role involves assisting employees with a range of HR tasks. ' +
                'These include managing vacation requests both present and future, ' +
                'reviewing past vacation usage, tracking remaining vacation days, and addressing general HR inquiries. ' +
                'You will rely on contextual details provided by users to fulfill their HR needs efficiently. ' +
                'When discussing dates, always use the YYYY-MM-DD format unless clarified otherwise by the user. ' +
                'If you are unsure about any details, do not hesitate to ask the user for clarification.' +
                'Use "you" to address the user directly, making it more personal and actionable.' +
                'Make sure the responses are direct, straightforward, and do not contain unnecessary information.'
            )
            .withFoundationModel('anthropic.claude-3-sonnet-20240229-v1:0')
            .withPreprocessingPrompt({
                promptType: PromptType.PRE_PROCESSING,
                promptState: PromptStateConfig.ENABLED,
                promptCreationMode: PromptConfig_Override,
                basePromptTemplate: customPreprocessingPrompt,
                inferenceConfiguration: {
                    temperature: 0.0,
                    topP: 1.0,
                    maximumLength: 2048,
                    stopSequences: ["</invoke>", "</answer>", "</error>"]
                },
                parserMode: PromptConfig_Override,
            })
            .withPostProcessingPrompt({
                promptType: PromptType.POST_PROCESSING,
                promptState: PromptStateConfig.ENABLED,
                promptCreationMode: PromptConfig_Override,
                basePromptTemplate: customPostProcessingPrompt,
                inferenceConfiguration: {
                    temperature: 1.0,
                    topP: 1.0,
                    maximumLength: 2048,
                    stopSequences: ["</invoke>", "</answer>", "</error>"]
                },
                parserMode: PromptConfig_Override,
            })
            .withPromptParserOverride(customParserFunction.functionArn) 
            .withUserInput()
            .build();


        // Function definitions that will be associated with the action group invocation 
        const getAvailableVacationDaysFunction = {
            name: 'get_available_vacation_days',
            description: 'Get the number of vacation days available for a certain employee',
            parameters: {
                employee_id: {
                    type: 'integer',
                    description: 'The ID of the employee to get the available vacations',
                    required: true
                }
            }
        };

        const reserveVacataionTimeFunction = {
            name: 'reserve_vacation_time',
            description: 'Reserve vacation time for a specific employee - you need all parameters to reserve vacation time',
            parameters: {
                employee_id: {
                    type: 'integer',
                    description: 'The ID of the employee to reserve the vacation time for',
                    required: true
                },
                start_date: {
                    type: 'integer',
                    description: 'The start date of the vacation time to reserve',
                    required: true
                },
                end_date: {
                    type: 'integer',
                    description: 'The end date of the vacation time to reserve',
                    required: true
                }
            }
        };


        // Create Agent Action Group
        const hrAssistanceAction = new AgentActionGroup(this, 'VacationsActionGroup', {
            actionGroupName: 'VacationsActionGroup',
            description: 'Actions for getting the number of available vacations days for an employee and confirm new time off',
            actionGroupExecutor: {
                lambdaDefinition: {
                    lambdaCode: readFileSync(join(__dirname, '..', '..', 'lambda', '01-agent-with-function-definitions', 'ag-assist-with-vacations-lambda.ts')),
                    lambdaHandler: 'handler',
                    lambdaRuntime: Runtime.NODEJS_18_X,
                    // codeSourceType: 'asset',
                    // fileName: 'agents-and-function-calling-for-bedrock-usecase-examples/lib/lambda/01-agent-with-function-definitions/ag-assist-with-vacations-lambda.ts',
                    timeoutInMinutes: 15,
                    environment: {
                        CLUSTER_ARN: auroraClusterArn,
                        SECRET_ARN: auroraDatbaseSecretArn,
                    },
                    managedPolicies: managedPolicies,
                    inlinePolicies: {
                        'AllowAccessSecretManagerPolicy': allowAccessSecretManagerPolicy
                    }
                }

            },
            schemaDefinition: {
                functionSchema: {
                    functions: [getAvailableVacationDaysFunction, reserveVacataionTimeFunction]
                }
            },
        });

        new BedrockAgentBlueprintsConstruct(this, 'AmazonBedrockAgentBlueprintsStack', {
            agentDefinition: agentDef,
            actionGroups: [hrAssistanceAction],
        });


    }

    createLambdaFunctionExecutionRole() {
        // Create a new role for the Lambda function
        const executionRole = new Role(this, 'LambdaExecutionRole', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
            description: 'Role to execute the custom parser Lambda function',
            managedPolicies: [
                ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
            ],
        });

        return executionRole;
    }

    // Create a custom AWS CloudFormation resource to execute the custom parser Lambda function
    createCustomParserResource() {
        const executionRole = this.createLambdaFunctionExecutionRole();

        // Create a new Lambda function that will be used as custom parser
        const customParserFunction = new NodejsFunction(this, 'CustomParserFunction', {
            runtime: Runtime.NODEJS_18_X,
            handler: 'handler',
            entry: join(__dirname, '..', '..', 'lambda', '04-agent-with-lambda-parser', 'cr-custom-lambda-parser.ts'),
            role: executionRole,
            timeout: Duration.minutes(5),
        });

        const provider = new Provider(this, 'CustomParserProvider', {
            onEventHandler: customParserFunction,
        });

        new CustomResource(this, 'CustomParserResource', {
            serviceToken: provider.serviceToken,
        });

        return { customParserFunction };
    }

}
