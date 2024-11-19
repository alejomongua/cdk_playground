#!/usr/bin/env python3
import os
import aws_cdk as cdk
from playground_1.playground_1_stack import Playground1Stack

app = cdk.App()
stack = Playground1Stack(app, "Playground1Stack",
                         env=cdk.Environment(account=os.getenv(
                              'CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
                         )

app.synth()
