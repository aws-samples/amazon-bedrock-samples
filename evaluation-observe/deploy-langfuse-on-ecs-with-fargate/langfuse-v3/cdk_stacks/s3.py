#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
)
from constructs import Construct

random.seed(47)


class S3BucketStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    S3_BUCKET_SUFFIX = ''.join(random.sample((string.ascii_lowercase + string.digits), k=7))

    self.blob_bucket = s3.Bucket(self, "BlobBucket",
      bucket_name=f'langfuse-blob-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}-{S3_BUCKET_SUFFIX}',
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      auto_delete_objects=True)

    self.event_bucket = s3.Bucket(self, "EventBucket",
      bucket_name=f'langfuse-event-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}-{S3_BUCKET_SUFFIX}',
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      auto_delete_objects=True)


    cdk.CfnOutput(self, 'BlobBucketName',
      value=self.blob_bucket.bucket_name,
      export_name=f'{self.stack_name}-BlobBucketName')
    cdk.CfnOutput(self, 'EventBucketName',
      value=self.event_bucket.bucket_name,
      export_name=f'{self.stack_name}-EventBucketName')
