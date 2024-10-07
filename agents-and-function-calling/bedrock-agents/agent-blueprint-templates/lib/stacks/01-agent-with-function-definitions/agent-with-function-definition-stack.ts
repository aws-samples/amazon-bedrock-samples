import { Stack, StackProps } from 'aws-cdk-lib'; 
import { Construct } from 'constructs';
import { join } from "path";
import { readFileSync } from 'fs'; 
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { Effect, ManagedPolicy, PolicyDocument, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { RDSDatabaseForAgentWithFD } from '../01-agent-with-function-definitions/rds-database-fd-construct';
import {BedrockAgentBlueprintsConstruct, AgentDefinitionBuilder, AgentActionGroup} from '@aws/agents-and-function-calling-for-amazon-bedrock-blueprints';


export class AgentWithFunctionDefinitionStack extends Stack {
    constructor(scope: Construct, id: string, props?: StackProps) {
        super(scope, id, props);

        // Define the Agent
        const agentDef = new AgentDefinitionBuilder(this, 'HRAssistantAgent', {})
            .withAgentName('hr-assistant-agent-with-function-definition')  
            .withInstruction(
                'As an HR agent, your role involves assisting employees with a range of HR tasks. ' +
                'These include managing vacation requests both present and future, ' +
                'reviewing past vacation usage, tracking remaining vacation days, and addressing general HR inquiries. ' +
                'You will rely on contextual details provided by employees to fulfill their HR needs efficiently. ' +
                'When discussing dates, always use the YYYY-MM-DD format unless clarified otherwise by the employee. ' +
                'If you are unsure about any details, do not hesitate to ask the employee for clarification.' +
                'Use "you" to address the employee directly, making it more personal and actionable.' +
                'Make sure the responses are direct, straightforward, and do not contain unnecessary information.'
            )
            .withFoundationModel('anthropic.claude-3-sonnet-20240229-v1:0')
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

        const rdsDatabase = new RDSDatabaseForAgentWithFD(this, 'RDSDatabaseForAgentWithFD');
        const auroraClusterArn = rdsDatabase.AuroraClusterArn;
        const auroraDatbaseSecretArn = rdsDatabase.AuroraDatabaseSecretArn;

        // Allow the Lambda function to access the Aurora Serverless and be able to query the database
        const managedPolicies = [
            ManagedPolicy.fromAwsManagedPolicyName('AmazonRDSDataFullAccess'),
        ];

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

        // Define the Action Group that will be associated with the Agent
        const hrAssistanceAction = new AgentActionGroup(this, 'VacationsActionGroup', {
            actionGroupName: 'VacationsActionGroup',
            description: 'Actions for getting the number of available vacations days for an employee and confirm new time off',
            actionGroupExecutor: {
                lambdaDefinition: {
                    lambdaCode: readFileSync(join(__dirname, '..', '..', 'lambda', '01-agent-with-function-definitions', 'ag-assist-with-vacations-lambda.ts')),
                    lambdaHandler: 'handler',
                    lambdaRuntime: Runtime.NODEJS_18_X,
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
                    functions: [getAvailableVacationDaysFunction, reserveVacataionTimeFunction]  // Function definitions that will be associated with the action group invocation
                }
            },
        });

        // Create the Agent Blueprint
        new BedrockAgentBlueprintsConstruct(this, 'AmazonBedrockAgentBlueprintsStack', {
            agentDefinition: agentDef,
            actionGroups: [hrAssistanceAction],
        });
    }
}


