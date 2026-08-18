#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Tear down the full bmkb-observability stack in REVERSE dependency order:
#   04 dashboards → 03 agent-runtime → 02 gateway → 01 knowledge-bases
# The 01 stack's ingest custom resource empties the KB source bucket on delete.
#
# Usage:
#   ./scripts/cleanup.sh [region] [project-name] [--purge-staging]
set -euo pipefail

REGION="${1:-us-west-2}"
PROJECT_NAME="${2:-bmkb-obs}"
PURGE_STAGING="${3:-}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"

del() {
  local stack="$1"
  if aws cloudformation describe-stacks --stack-name "$stack" --region "$REGION" >/dev/null 2>&1; then
    echo "-- deleting ${stack} --"
    aws cloudformation delete-stack --stack-name "$stack" --region "$REGION"
    aws cloudformation wait stack-delete-complete --stack-name "$stack" --region "$REGION" \
      && echo "   ${stack} deleted" || echo "   WARN: ${stack} delete did not complete cleanly"
  else
    echo "-- ${stack} not present, skipping --"
  fi
}

echo "== Tearing down ${PROJECT_NAME} in ${REGION} (account ${ACCOUNT_ID}) =="
del "${PROJECT_NAME}-dashboards"
del "${PROJECT_NAME}-agent"
del "${PROJECT_NAME}-gateway"
del "${PROJECT_NAME}-kb"

if [ "$PURGE_STAGING" = "--purge-staging" ]; then
  STAGING_BUCKET="${PROJECT_NAME}-cfn-staging-${ACCOUNT_ID}-${REGION}"
  echo "-- purging staging bucket ${STAGING_BUCKET} --"
  aws s3 rb "s3://${STAGING_BUCKET}" --force --region "$REGION" || true
fi
echo "== Cleanup complete =="
