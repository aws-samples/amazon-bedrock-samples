# Cross-Border KYC Agent — Amazon Bedrock + LangGraph + OpenRegistry MCP

This example demonstrates an agent built with **Amazon Bedrock** (Anthropic Claude Sonnet 4.5) and **LangGraph** that connects to the **[OpenRegistry](https://openregistry.sophymarine.com) MCP server** to perform live **cross-border Know-Your-Business (KYB) / Beneficial-Ownership (UBO) chain walking** across **27 national company registries** (UK Companies House, Germany Handelsregister, France Sirene+RNE, Italy InfoCamere via EU BRIS, Spain BORME, Korea OPENDART, plus 21 more).

**Functionality:**

1. **Search a company** in any of the 27 national registries by name or local company-number format.
2. **Pull the statutory profile, officers, and Persons with Significant Control (PSC / UBO)** for that entity, with every field name preserved verbatim from the upstream government register.
3. **Walk the corporate-ownership chain across borders** — when a PSC is itself a corporate entity, the agent recurses into that entity's home jurisdiction and continues until it reaches an individual, an AML-gated register (CJEU C-37/20 — DE/ES/IT/NL/LU/AT/MT/PT), or a configurable depth cap.
4. **Surface AML gates honestly** — when the upstream register returns HTTP `501 alternative_url`, the agent reports the statutory channel rather than substituting commercial-aggregator data.
5. **Cite every fact** to the registry + identifier, so the answer is auditable back to the government source.

## Why MCP (and not a custom tool function)?

OpenRegistry's tool surface — about 30 tools across the 27 registries — updates as new countries come online. Wiring it as a remote Streamable-HTTP MCP server means the agent **discovers tools at runtime** via the MCP `tools/list` RPC, so this notebook stays small and you don't have to update Python wrappers when the registry grows.

## Prerequisites

You will need the following before running this notebook. We use the `us-west-2` Region by default; for available Regions, see [Amazon Bedrock endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock.html).

- A valid AWS account.
- An AWS IAM role with permission to invoke Bedrock models. If you're running on a SageMaker notebook instance you'll also need permissions to manage SageMaker resources. Administrator access works.
- Access to **Anthropic Claude Sonnet 4.5** (or Sonnet 3.5 / Haiku as a substitute) enabled in Amazon Bedrock — see [Access foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).
- **No OpenRegistry API key needed** — the notebook uses the free anonymous tier (20 req/min/IP, 3-country fan-out). For higher rate limits or batch onboarding, complete the OAuth 2.1 flow at [openregistry.sophymarine.com/account](https://openregistry.sophymarine.com/account) and pass the token via `OPENREGISTRY_TOKEN`.

## Run

Open `bedrock_openregistry_kyc_agent.ipynb` in Jupyter or SageMaker. Run cells top-to-bottom. The final cell asks Claude on Bedrock to walk Revolut Ltd's PSC chain — you'll see ~5–10 live MCP tool calls against UK Companies House (and any cross-border parents the chain hits) before Claude returns a cited summary.

## What's covered (and what's not)

**Covered**: company profile, officers, PSC/UBO, shareholders, charges, filings index, raw filing documents (PDF / iXBRL / XBRL), statutory accounts, name-availability, address standardisation across 27 jurisdictions.

**Not covered**: credit scores, sanctions list screening, PEP screening, US private-company financials. OpenRegistry is a passthrough to the *registry* — for those layers, integrate a separate sanctions-list MCP or Bedrock Action Group.

## Costs

Bedrock model invocations are billed per the Bedrock price list. OpenRegistry is free on the anonymous tier; paid tiers ($9–$29/mo) buy higher rate limits and cross-border fan-out, but no data is paywalled.

## License

This sample is licensed under MIT-0 (matching the rest of `aws-samples/amazon-bedrock-samples`). OpenRegistry is a platform by [Sophymarine](https://sophymarine.com); their docs are CC-BY-4.0.
