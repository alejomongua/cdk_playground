import aws_cdk as core
import aws_cdk.assertions as assertions

from playground_1.playground_1_stack import Playground1Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in playground_1/playground_1_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Playground1Stack(app, "playground-1")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
