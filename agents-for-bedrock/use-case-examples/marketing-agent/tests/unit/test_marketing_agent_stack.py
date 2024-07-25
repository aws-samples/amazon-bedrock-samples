import aws_cdk as core
import aws_cdk.assertions as assertions

from marketing_agent.marketing_agent_stack import MarketingAgentStack

# example tests. To run these tests, uncomment this file along with the example
# resource in marketing_agent/marketing_agent_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MarketingAgentStack(app, "marketing-agent")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
