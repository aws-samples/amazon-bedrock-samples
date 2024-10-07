from aws_cdk import App, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_glue as glue
from aws_cdk import aws_iam as iam
from aws_cdk.aws_s3_deployment import BucketDeployment, Source
import aws_cdk as cdk
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from cdklabs.generative_ai_cdk_constructs import (
    bedrock)

from cdklabs.generative_ai_cdk_constructs.bedrock import (
    Agent, ApiSchema, BedrockFoundationModel,AgentActionGroup
)
from aws_cdk import aws_events as events
from aws_cdk import aws_cloudformation as cfn

from aws_cdk import aws_events_targets as events_targets
# from aws_cdk import custom_resources
#from aws_cdk import core as cdk
from aws_cdk import Duration  # Import Duration directly
from cdklabs.generative_ai_cdk_constructs.bedrock import ActionGroupExecutor


from constructs import Construct
from agent_instruction_generator import analyze_csv_files,generate_instruction,invoke_claude_3_with_text

from Prep_Data import prep_data

class MyStack(Stack):
    def __init__(self, scope: App, id: str,zip_file_name: str, region: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # General setup
        #region = cdk.Stack.of(self).region
        account_id = cdk.Stack.of(self).account
       
        #zip_file_name='EV_WA.zip'
        
        
        data_folder_name=zip_file_name.replace('.zip','')
        agent_name = f"agent_{data_folder_name.lower()}"
        suffix = f"{region}-{account_id}-{agent_name.lower()}"

        lambda_role_name = f'{agent_name}-lambda-role-{suffix}'
        agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{suffix}'
        lambda_name = f'{agent_name}-{suffix}'
    
        foundation_model = BedrockFoundationModel('anthropic.claude-3-sonnet-20240229-v1:0', supports_agents=True)
        
        
        prep_data(data_folder_name)
        
        glue_database_name = f"{data_folder_name.lower()}"
        # Create an S3 bucket
        schema_bucket = s3.Bucket(self, "SchemaBucket",removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)

        # Upload files to S3
        # Upload the unzipped data to S3
        deployment = BucketDeployment(self, "DeployFiles",
                                      sources=[Source.asset(f"./Data/{data_folder_name}")], 
                                      destination_bucket=schema_bucket,
                                      destination_key_prefix=f"data/{data_folder_name}/")

        # Define the IAM role for Glue
        glue_role = iam.Role(self, "GlueRole",
                             assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                             managed_policies=[
                                 iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
                                 iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
                             ])
        glue_database = glue.CfnDatabase(self, "GlueDatabase",
            catalog_id=account_id,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=glue_database_name
            )
        )
        # Create a Glue Crawler
        crawler_name = "MyCrawler"  # Define the crawler name as a variable
        crawler = glue.CfnCrawler(self, crawler_name,
                                role=glue_role.role_arn,
                                database_name=glue_database_name,
                                schedule=glue.CfnCrawler.ScheduleProperty(
                                                schedule_expression="cron(0/1 * * * ? *)"
                                            ),
                                targets={"s3Targets": [{
                                    "path": f"s3://{schema_bucket.bucket_name}/data/{data_folder_name}/"
                                }]})

        
      
       
        
        
        athena_result_loc = f"s3://{schema_bucket.bucket_name}/athena_result/"

        

        # Create a Lambda function for action group
        action_group_function = lambda_.Function(
            self,
            "ActionGroupFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("./lambda/agent/"),
            environment={
              'outputLocation': athena_result_loc,
              'glue_database_name': glue_database_name,
              'region':region,
              'bucket_name':schema_bucket.bucket_name
            },
            
            timeout= Duration.minutes(5),
            memory_size=512,
        )
        
        
        # action_group_function = PythonFunction(
        #     self,
        #     "ActionGroupFunction",
        #     runtime=Runtime.PYTHON_3_9,
        #     entry="./lambda",  
        #     index="app.py",
        #     handler="lambda_handler",
        # )
        
        # Fine-tuning IAM policies
        action_group_function.role.add_to_policy(iam.PolicyStatement(
            actions=["glue:StartJobRun"],
            resources=[f"arn:aws:glue:{region}:{account_id}:job/*"]
        ))
        action_group_function.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables",
                "glue:BatchGetPartition", "glue:GetPartition", "glue:GetPartitions",
                "glue:BatchCreatePartition", "glue:CreatePartition", "glue:DeletePartition",
                "glue:UpdatePartition", "glue:BatchDeletePartition"
            ],
            resources=[f"arn:aws:glue:{region}:{account_id}:catalog",
                       f"arn:aws:glue:{region}:{account_id}:database/{glue_database_name}",
                       f"arn:aws:glue:{region}:{account_id}:table/{glue_database_name}/*"]
        ))
        action_group_function.role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket","s3:CreateBucket", "s3:GetBucketLocation"],
            resources=[f"{schema_bucket.bucket_arn}", f"{schema_bucket.bucket_arn}/*"]
        ))
        action_group_function.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "athena:StartQueryExecution", "athena:GetQueryExecution",
                "athena:GetQueryResults", "athena:StopQueryExecution",
                "athena:GetWorkGroup"
            ],
            resources=[f"arn:aws:athena:{region}:{account_id}:workgroup/primary"]
        ))

        
        
        data_folder = f'./Data/{data_folder_name}'

        data_context = analyze_csv_files(data_folder)
        
        instruction_text = generate_instruction(data_context, glue_database_name)
        # question = f"""
        #     Please craft a comprehensive, single-paragraph instruction (up to 1200 words) for the Bedrock agent. Incorporate all the contextual details provided below to develop this instruction text. The final submission should consist solely of this detailed instruction.\n
        #     {instruction_text}.
        #     """ 
            
        
        question = f"""
            Craft a comprehensive and cohesive paragraph instruction for the Bedrock agent, ensuring the instruction text includes all 7 contextual details and examples provided. The instruction should be detailed, precise with a maximum length of 4000 characters. Clearly outline the agent's tasks and how it should interact with users, incorporating the provided contextual details and examples with minimal changes. Avoid any introductory phrases such as "Here is your...".

            <Contextual details and examples>
            {instruction_text}
            """
   
                 
        agent_instruction=invoke_claude_3_with_text(question)    
        print(agent_instruction)
        
        api_schema = ApiSchema.from_asset("./text_to_sql_openapi_schema.json")
        agent = Agent(
            self,
            "MyAgent",
            foundation_model=foundation_model,
            instruction=agent_instruction,
            description="Agent for performing sql queries.",
            should_prepare_agent=True
          
        )
        # agent.add_alias(self, 'ProdAlias', 
        #     alias_name='prod',
        #     agent_version='1'
        #     )   
        
      

        action_group = AgentActionGroup(
            self,
            "MyActionGroup",
            action_group_name="QueryAthenaActionGroup",
            description="Actions for getting the database schema and querying the Athena database for sample data or final query.",
            action_group_executor=ActionGroupExecutor(lambda_=action_group_function),  
            action_group_state="ENABLED",
            api_schema=api_schema
        )
        
       
        
        agent.add_action_group(action_group)
       
        
         # IAM Role for Agent
        agent_role = iam.Role(self, "AgentRole",
                              assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
                            )

        # Attach IAM policies for agent to interact with AWS services
        agent_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[schema_bucket.bucket_arn, f"{schema_bucket.bucket_arn}/*"]
        ))
        
        action_group_function.add_permission(
            "AllowBedrockInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{region}:{account_id}:agent/*"
        )
        print("agent id:",agent.agent_id,agent.agent_arn)


app = App()
zip_file_name = app.node.try_get_context("zip_file_name")
region = app.node.try_get_context("region")
MyStack(app, "text-2-sql2", zip_file_name=zip_file_name, region=region)
app.synth()
