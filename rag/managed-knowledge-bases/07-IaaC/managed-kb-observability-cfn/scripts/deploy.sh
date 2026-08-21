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
# Deploy the full agentic-RAG stack in order, narrating each stage:
#   [1/4] knowledge-bases → [2/4] agentic-gateway → [3/4] agent-runtime → [4/4] dashboards
# Outputs are wired forward automatically (KB ids + gateway ARN → dashboards), and each
# stage prints a live-verification line so you can watch the solution come up.
#
# Usage:
#   ./scripts/deploy.sh [region] [project-name]
#   ./scripts/deploy.sh us-west-2 bmkb-obs
#
# Stack [3/4] builds the agent container via CodeBuild — allow ~8–10 min.
set -euo pipefail

REGION="${1:-us-west-2}"
PROJECT_NAME="${2:-bmkb-obs}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── pretty output helpers ─────────────────────────────────────────────────
if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; C=$'\033[36m'; Y=$'\033[33m'; R=$'\033[0m'; else B=; G=; C=; Y=; R=; fi
banner() { echo; echo "${C}════════════════════ ${B}$1${R}${C} ════════════════════${R}"; }
ok()     { echo "  ${G}✓${R} $1"; }
info()   { echo "  ${Y}→${R} $1"; }

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
STAGING_BUCKET="${PROJECT_NAME}-cfn-staging-${ACCOUNT_ID}-${REGION}"

KB_STACK="${PROJECT_NAME}-kb"
GW_STACK="${PROJECT_NAME}-gateway"
AGENT_STACK="${PROJECT_NAME}-agent"
DASH_STACK="${PROJECT_NAME}-dashboards"

out()  { aws cloudformation describe-stacks --stack-name "$1" --region "$REGION" \
           --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text; }

echo "${B}Agentic RAG on a Managed Bedrock Knowledge Base — CloudFormation deploy${R}"
echo "Account ${ACCOUNT_ID} · Region ${REGION} · Project ${PROJECT_NAME}"

# ── [1/4] Knowledge bases + ingestion ─────────────────────────────────────
banner "[1/4] Knowledge Bases"
info "packaging ingest Lambda + bundled synthetic corpora"
rm -rf build/ingest_sync
mkdir -p build/ingest_sync/corpora
cp lambdas/ingest_sync/index.py build/ingest_sync/
cp -R data/financial build/ingest_sync/corpora/financial
cp -R data/weather   build/ingest_sync/corpora/weather

if ! aws s3api head-bucket --bucket "$STAGING_BUCKET" --region "$REGION" 2>/dev/null; then
  info "creating CFN staging bucket ${STAGING_BUCKET}"
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$STAGING_BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$STAGING_BUCKET" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
  fi
fi

aws cloudformation package \
  --template-file templates/01-knowledge-bases.yaml \
  --s3-bucket "$STAGING_BUCKET" \
  --output-template-file build/01-knowledge-bases.packaged.yaml \
  --region "$REGION" >/dev/null
info "deploying ${KB_STACK} (2 managed KBs + data sources + ingestion)"
aws cloudformation deploy \
  --template-file build/01-knowledge-bases.packaged.yaml \
  --stack-name "$KB_STACK" \
  --parameter-overrides ProjectName="$PROJECT_NAME" \
  --capabilities CAPABILITY_NAMED_IAM --region "$REGION"

FIN_KB="$(out "$KB_STACK" FinancialKnowledgeBaseId)"
WEA_KB="$(out "$KB_STACK" WeatherKnowledgeBaseId)"
for kb_pair in "financial:${FIN_KB}" "weather:${WEA_KB}"; do
  theme="${kb_pair%%:*}"; kb="${kb_pair##*:}"
  st="$(aws bedrock-agent get-knowledge-base --knowledge-base-id "$kb" --region "$REGION" --query 'knowledgeBase.status' --output text 2>/dev/null || echo '?')"
  ok "${theme} KB ${kb}  ${st}"
done
ok "ingestion custom resource completed (corpora uploaded + synced)"

# ── [2/4] Gateway + per-KB agentic targets ────────────────────────────────
banner "[2/4] Agentic Gateway"
info "deploying ${GW_STACK} (Gateway AWS_IAM/MCP + per-KB AgenticRetrieveStream targets)"
aws cloudformation deploy \
  --template-file templates/02-agentic-gateway.yaml \
  --stack-name "$GW_STACK" \
  --parameter-overrides ProjectName="$PROJECT_NAME" \
  --capabilities CAPABILITY_NAMED_IAM --region "$REGION"

GW_ARN="$(out "$GW_STACK" GatewayArn)"
GW_ID="$(out "$GW_STACK" GatewayId)"
GW_ST="$(aws bedrock-agentcore-control get-gateway --gateway-identifier "$GW_ID" --region "$REGION" --query 'status' --output text 2>/dev/null || echo '?')"
ok "gateway ${GW_ID}  ${GW_ST}"
TCOUNT="$(aws bedrock-agentcore-control list-gateway-targets --gateway-identifier "$GW_ID" --region "$REGION" --query 'length(items)' --output text 2>/dev/null || echo '?')"
ok "${TCOUNT} KB targets attached (financial + weather, AgenticRetrieveStream)"

# ── [3/4] Instrumented Strands agent on Runtime (CodeBuild image) ──────────
banner "[3/4] Agent Runtime  (CodeBuild image build — ~8–10 min)"
info "deploying ${AGENT_STACK} (ECR + CodeBuild + Runtime + vended logs/traces + online eval)"
aws cloudformation deploy \
  --template-file templates/03-agent-runtime.yaml \
  --stack-name "$AGENT_STACK" \
  --parameter-overrides ProjectName="$PROJECT_NAME" \
  --capabilities CAPABILITY_NAMED_IAM --region "$REGION"

AGENT_ID="$(out "$AGENT_STACK" AgentRuntimeId)"
AGENT_ST="$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$AGENT_ID" --region "$REGION" --query 'status' --output text 2>/dev/null || echo '?')"
ok "agent runtime ${AGENT_ID}  ${AGENT_ST}"
ok "online evaluation config ENABLED (continuous scoring of live sessions)"

# ── [4/4] Dashboards (wired with KB ids + gateway ARN) ─────────────────────
banner "[4/4] Dashboards"
info "deploying ${DASH_STACK} (agentic-observability + kb-observability)"
aws cloudformation deploy \
  --template-file templates/04-dashboards.yaml \
  --stack-name "$DASH_STACK" \
  --parameter-overrides ProjectName="$PROJECT_NAME" \
    FinancialKbId="$FIN_KB" WeatherKbId="$WEA_KB" GatewayArn="$GW_ARN" \
  --region "$REGION"
ok "2 CloudWatch dashboards created"

# ── Summary ────────────────────────────────────────────────────────────────
banner "Deploy complete"
echo "  Dashboards (empty until you drive traffic):"
echo "    ${C}$(out "$DASH_STACK" ObservabilityDashboardUrl)${R}"
echo "    ${C}$(out "$DASH_STACK" KbObservabilityDashboardUrl)${R}"
echo
echo "  ${B}Next:${R} run notebooks/01-drive-and-observe.ipynb to drive traffic and fill the dashboards."
