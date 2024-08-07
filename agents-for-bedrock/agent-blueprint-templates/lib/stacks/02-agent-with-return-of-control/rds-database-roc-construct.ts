
import { Duration, RemovalPolicy, aws_rds as rds } from "aws-cdk-lib";
import { Effect, ManagedPolicy, PolicyDocument, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import { Runtime } from "aws-cdk-lib/aws-lambda";
import { NodejsFunction } from "aws-cdk-lib/aws-lambda-nodejs";
import { AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId } from "aws-cdk-lib/custom-resources";
import { Construct } from "constructs";
import { join } from "path";



export class RDSDatabaseForAgentWithROC extends Construct {
    public readonly dbSecret: rds.DatabaseSecret;
    public readonly dbCluster: rds.ServerlessCluster;
    public readonly AuroraClusterArn: string;
    public readonly AuroraDatabaseSecretArn: string;

    constructor(scope: Construct, id: string) {
        super(scope, id);


        this.dbSecret = new rds.DatabaseSecret(this, 'AuroraSecretForAgentWithROC', {
            username: 'clusteradmin',
        });

        // Define Aurora Serverless cluster
        this.dbCluster = new rds.ServerlessCluster(this, 'AuroraClusterForAgentWithROC', {
            engine: rds.DatabaseClusterEngine.auroraPostgres({
                version: rds.AuroraPostgresEngineVersion.VER_13_12,
            }),
            clusterIdentifier: 'agent-with-roc-aurora-cluster',
            defaultDatabaseName: 'employeedatabase',
            credentials: rds.Credentials.fromSecret(this.dbSecret),
            enableDataApi: true,
            removalPolicy: RemovalPolicy.DESTROY,
        });


        // Create a new Lambda function to populate sample data in the Aurora Serverless database
        const executionRole = this.createLambdaFunctionExecutionRole();
        const populateSampleDataFunction = new NodejsFunction(this, 'PopulateSampleDataFunc', {
            runtime: Runtime.NODEJS_18_X,
            handler: 'handler',
            entry: join(__dirname, '..', '..', 'lambda', '02-agent-with-return-of-control', 'cr-populate-data-in-rds.ts'),
            role: executionRole,
            timeout: Duration.minutes(5), 
            environment: {    //  Pass the cluster ARN and secret ARN as env variables, so we can use them in the Lambda functions code. 
                CLUSTER_ARN: this.dbCluster.clusterArn,
                SECRET_ARN: this.dbCluster.secret?.secretArn || '',
            }
        });

        // Policy statement to grant permission to invoke the Lambda function - populateSampleDataFunction
        const invokePermission = new PolicyStatement({
            actions: ['lambda:InvokeFunction'],
            resources: [populateSampleDataFunction.functionArn],
        });


        // Grants the necessary permissions for the custom resource 
        const customResourcePolicy = AwsCustomResourcePolicy.fromStatements([invokePermission]);


        // Create a custom resource to trigger the execution of populateSampleDataFunction Lambda function whenever the stack is updated
        new AwsCustomResource(this, 'TriggerPopulateDataFunction', {
            onUpdate: {
                service: 'Lambda',
                action: 'InvokeCommand',
                parameters: {
                    FunctionName: populateSampleDataFunction.functionName,
                    Payload: JSON.stringify({ message: 'Populate data in RDS' }),
                },
                physicalResourceId: PhysicalResourceId.of(Date.now().toString()),
            },
            policy: customResourcePolicy,
        });

        this.AuroraClusterArn = this.dbCluster.clusterArn;
        this.AuroraDatabaseSecretArn = this.dbSecret.secretArn;

    }


    createLambdaFunctionExecutionRole() {
        const lambdaRole = new Role(this, 'LambdaRoleToPopulateData', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
            description: 'Execution Role for Lambda function',
            managedPolicies: [
                ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
                ManagedPolicy.fromAwsManagedPolicyName('AmazonRDSDataFullAccess')  //NOTE: Adding this role to have Lambda access RDS database
            ],
            inlinePolicies: {
                'AllowAccessSecretManager': new PolicyDocument({
                    statements: [
                        new PolicyStatement({
                            effect: Effect.ALLOW,
                            actions: ['secretsmanager:GetSecretValue'],
                            resources: [this.dbSecret.secretArn]
                        })
                    ]
                })
            }
        });

        return lambdaRole;
    }
}



