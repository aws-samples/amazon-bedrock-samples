from aws_cdk import (
  Construct,
  Stack,
  aws_ec2 as ec2,
  aws_rds as rds,
  aws_lambda as lambda_,
  aws_iam as iam,
  aws_logs as logs,
  custom_resource as cr,
  RemovalPolicy,
  Duration
)
from constructs import Construct

class RdsAuroraPostgreSqlProps(Construct):
  def __init__(
      self,
      cluster_id: str,
      cluster_engine: rds.IClusterEngine,
      instance_class: rds.InstanceClass,
      instance_size: rds.InstanceSize,
      db_subnet_group_name: str,
      instance_id: str,
      vpc: ec2.Vpc,
      database_name: str,
      table_name: str,
      schema_name: str,
      user_name: str,
      embedding_model_id: str,
      region: str,
      account_id: str,
      table_creator_prefix: str
  ):
      self.cluster_id = cluster_id
      self.cluster_engine = cluster_engine
      self.instance_class = instance_class
      self.instance_size = instance_size
      self.db_subnet_group_name = db_subnet_group_name
      self.instance_id = instance_id
      self.vpc = vpc
      self.database_name = database_name
      self.table_name = table_name
      self.schema_name = schema_name
      self.user_name = user_name
      self.embedding_model_id = embedding_model_id
      self.region = region
      self.account_id = account_id
      self.table_creator_prefix = table_creator_prefix

class RdsAuroraPostgreSql(Construct):
  def __init__(self, scope: Construct, id: str, props: RdsAuroraPostgreSqlProps, **kwargs):
      super().__init__(scope, id, **kwargs)

      self.cluster = self.create_rds_cluster(props)
      self.secret_arn = self.cluster.secret_arn  # By default, RDS creates a secret with the master username & password
      self.create_rds_table(props)

  def create_rds_cluster(self, props: RdsAuroraPostgreSqlProps) -> rds.DatabaseCluster:
      vpc = props.vpc
      cluster_subnet_props: rds.SubnetGroupProps = {
          "subnet_group_name": props.db_subnet_group_name,
          "vpc": vpc,
          "description": "RDS Cluster subnet group used by CFN tests",
          "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
      }
      cluster_subnet_group = rds.SubnetGroup(self, "ClusterSubnetGroup", **cluster_subnet_props)
      rds_cluster = rds.DatabaseCluster(
          self,
          "Cluster",
          engine=props.cluster_engine or rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_15_4),
          vpc=vpc,
          instance_identifiers=["writer"],
          instances=rds.InstanceProps(
              instance_type=ec2.InstanceType.of(props.instance_class, props.instance_size),
              performance_insights_enabled=False,
              instance_identifier=props.instance_id,
              publicly_accessible=True
          ),
          subnet_group=cluster_subnet_group,
          cluster_identifier=props.cluster_id,
          credentials=rds.Credentials.from_generated_secret("postgres")
      )

      # enableHttpEndpoint is not available in the L2 construct - overriding it using the L1 construct
      cfn_rds_cluster = rds_cluster.node.default_child
      cfn_rds_cluster.enable_http_endpoint = True

      return rds_cluster

  def create_rds_table(self, props: RdsAuroraPostgreSqlProps):
      rds_table_creation_lambda = lambda_.Function(
          self,
          "BKB-RDS-InfraSetupLambda",
          function_name=f"{props.table_creator_prefix}-BKB-RDS-InfraSetupLambda",
          code=lambda_.Code.from_asset("path/to/lambda/code"),
          handler="amazon_bedrock_knowledge_base_infra_setup_lambda.rds_handler.handler",
          role=iam.Role(
              self,
              "LambdaRole",
              assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
              managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
          ),
          memory_size=1024,
          timeout=Duration.minutes(14),
          runtime=lambda_.Runtime.PYTHON_3_8,
          tracing=lambda_.Tracing.ACTIVE,
          current_version_options=lambda_.VersionOptions(removal_policy=RemovalPolicy.DESTROY),
          environment={
              "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
              "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
              "POWERTOOLS_LOG_LEVEL": "INFO"
          }
      )

      rds_table_creation_provider = cr.Provider(
          self,
          "RDSTableCreationProvider",
          on_event_handler=rds_table_creation_lambda,
          log_group=logs.LogGroup(
              self,
              "RDSTableCreationProviderLogs",
              retention=logs.RetentionDays.ONE_DAY
          ),
          role=iam.Role(
              self,
              "RDSProviderRole",
              assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
              managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
          )
      )

      table_creation_custom_resource = cr.CustomResource(
          self,
          "RDSTableCreationCustomResource",
          service_token=rds_table_creation_provider.service_token,
          properties={
              "database_name": props.database_name,
              "table_name": props.table_name,
              "schema_name": props.schema_name,
              "user_name": props.user_name,
              "cluster_arn": self.get_rds_cluster_arn(props.region, props.account_id, self.cluster.cluster_identifier),
              "secret_arn": self.secret_arn,
              "embedding_model_id": props.embedding_model_id
          }
      )
      table_creation_custom_resource.node.add_dependency(rds_table_creation_lambda)

  def get_rds_cluster_arn(self, region: str, account_id: str, cluster_identifier: str) -> str:
      return f"arn:aws:rds:{region}:{account_id}:cluster:{cluster_identifier}"
```
