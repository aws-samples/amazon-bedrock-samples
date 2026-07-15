# Managed Knowledge Bases — Security Patterns

Jupyter notebooks demonstrating security patterns for Amazon Bedrock Managed Knowledge Bases, from direct SDK access to full governance with AgentCore Gateway, Cedar policies, JWT authentication, and Lambda interceptors.

## Patterns

All notebooks are in the `notebooks/` directory.

| # | Notebook | Description | Complexity |
|---|---|---|---|
| 1 | `01-direct-sdk.ipynb` | Direct SDK access with IAM — no Gateway | ⭐ |
| 2 | `02-metadata-filters.ipynb` | Metadata filtering for document-level scoping | ⭐⭐ |
| 3 | `03-gateway-iam.ipynb` | AgentCore Gateway with IAM auth | ⭐⭐ |
| 4 | `04-gateway-cedar.ipynb` | Gateway + Cedar Policy Engine (permit/deny per target) | ⭐⭐⭐ |
| 5 | `05-gateway-jwt-cognito.ipynb` | Gateway + JWT auth via Cognito | ⭐⭐⭐ |
| 6 | `06-gateway-jwt-cedar.ipynb` | Gateway + JWT + Cedar (multi-tenant, per-department) | ⭐⭐⭐⭐ |
| 7 | `07-gateway-interceptor.ipynb` | Gateway + Lambda interceptor (dynamic filter injection) | ⭐⭐⭐⭐ |
| 8 | `08-full-governance.ipynb` | Full stack: JWT + Cedar + Interceptor + metadata filters | ⭐⭐⭐⭐⭐ |

## Quick Start

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01-direct-sdk.ipynb
```

## Configuration

Edit the configuration cell at the top of each notebook:

```python
REGION = "us-west-2"
ROLE_ARN = "<your-kb-execution-role-arn>"       # IAM role for KB execution
GW_ROLE_ARN = "<your-gateway-role-arn>"         # IAM role for Gateway (patterns 3-8)
S3_BUCKET = "<your-bucket>"
S3_ACCOUNT = "<your-account-id>"
S3_PREFIX = "<your-prefix>/"
```

### Required IAM Permissions

- **KB Role**: Bedrock KB execution, S3 read access to your document bucket
- **Gateway Role** (patterns 3-8): Bedrock AgentCore Gateway execution, KB invoke permissions
- **Lambda Role** (patterns 7-8): Lambda execution, CloudWatch Logs

## Project Structure

```
04-security-and-access-controls/
├── notebooks/
│   ├── 01-direct-sdk.ipynb
│   ├── 02-metadata-filters.ipynb
│   ├── 03-gateway-iam.ipynb
│   ├── 04-gateway-cedar.ipynb
│   ├── 05-gateway-jwt-cognito.ipynb
│   ├── 06-gateway-jwt-cedar.ipynb
│   ├── 07-gateway-interceptor.ipynb
│   ├── 08-full-governance.ipynb
│   └── util.py
├── diagrams/               # Architecture diagrams (.drawio)
├── website/                # Static HTML documentation
├── requirements.txt
└── README.md
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Security Layers                            │
│                                                              │
│  Layer 1: Authentication (IAM / JWT / None)                  │
│  Layer 2: Authorization (Cedar Policy Engine)                │
│  Layer 3: Request Processing (Lambda Interceptors)           │
│  Layer 4: Target Configuration (admin-set KB + filters)      │
│  Layer 5: Document Scoping (metadata filters per query)      │
└──────────────────────────────────────────────────────────────┘
```

## Documentation

- [AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [Cedar Policy Engine](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html)
- [Gateway inbound authorization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)
