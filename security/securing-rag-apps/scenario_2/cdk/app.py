#!/usr/bin/env python3

import aws_cdk as cdk

from pii_mask_during_retrieval.pii_mask_during_retrieval_stack import (
    PiiMaskDuringRetrievalStack,
)


app = cdk.App()
PiiMaskDuringRetrievalStack(app, "PiiMaskDuringRetrievalStack")

app.synth()
