from constructs import Construct
from aws_cdk import (
    aws_dynamodb as ddb,
    RemovalPolicy
)

class DynamoDB(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        dependencies: list = []
    ):
        super().__init__(scope, id)

        self.id = id
        self.dependencies = dependencies

    def build(self):
        table = ddb.Table(
            self,
            f"{self.id}_auto_pricing",
            partition_key=ddb.Attribute(
                name="composite_pk",
                type=ddb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        table.add_global_secondary_index(
            index_name="model_name_index",
            partition_key=ddb.Attribute(
                name="model_name",
                type=ddb.AttributeType.STRING
            ),
            projection_type=ddb.ProjectionType.ALL
        )

        table.add_global_secondary_index(
            index_name="year_index",
            partition_key=ddb.Attribute(
                name="year",
                type=ddb.AttributeType.NUMBER
            ),
            projection_type=ddb.ProjectionType.ALL
        )

        for el in self.dependencies:
            table.node.add_dependency(el)

        return table
