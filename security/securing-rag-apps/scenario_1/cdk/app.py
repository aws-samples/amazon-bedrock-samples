#!/usr/bin/env python3

import aws_cdk as cdk

from cdk_pii_scenario1.cdk_pii_scenario1_stack import PiiRedactionStack

app = cdk.App()
PiiRedactionStack(app, "CdkPiiScenario1Stack")
app.synth()
