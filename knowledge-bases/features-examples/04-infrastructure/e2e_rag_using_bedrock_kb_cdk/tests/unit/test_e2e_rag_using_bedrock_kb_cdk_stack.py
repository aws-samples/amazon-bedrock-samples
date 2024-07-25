import aws_cdk as core
import aws_cdk.assertions as assertions

from e2e_rag_using_bedrock_kb_cdk.e2e_rag_using_bedrock_kb_cdk_stack import E2ERagUsingBedrockKbCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in e2e_rag_using_bedrock_kb_cdk/e2e_rag_using_bedrock_kb_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = E2ERagUsingBedrockKbCdkStack(app, "e2e-rag-using-bedrock-kb-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
