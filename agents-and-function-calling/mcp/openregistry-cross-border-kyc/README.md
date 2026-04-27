# Cross-Border KYC Agent — Amazon Bedrock + LangGraph + OpenRegistry MCP

This example demonstrates an agent built with **Amazon Bedrock** (Anthropic Claude Sonnet 4.5) and **LangGraph** that connects to the **[OpenRegistry](https://openregistry.sophymarine.com) MCP server** to perform live **cross-border Know-Your-Business (KYB) / Beneficial-Ownership (UBO) chain walking** across **27 national company registries** (UK Companies House, Germany Handelsregister, France Sirene+RNE, Italy InfoCamere via EU BRIS, Spain BORME, Korea OPENDART, plus 21 more).

**Functionality:**

1. **Search a company** in any of the 27 national registries by name or local company-number format.
2. **Pull the statutory profile, officers, and Persons with Significant Control (PSC / UBO)** for that entity, with every field name preserved verbatim from the upstream government register.
3. **Walk the corporate-ownership chain across borders** — when a PSC is itself a corporate entity, the agent recurses into that entity's home jurisdiction and continues until it reaches an individual, an AML-gated register (CJEU C-37/20 — DE/ES/IT/NL/LU/AT/MT/PT), or a configurable depth cap.
4. **Surface AML gates honestly** — when the upstream register returns HTTP `501 alternative_url`, the agent reports the statutory channel rather than substituting commercial-aggregator data.
5. **Cite every fact** to the registry + identifier, so the answer is auditable back to the government source.

## All 30 jurisdictions covered

The agent talks to a single MCP endpoint, but that endpoint covers every jurisdiction below. Each row is the native registry name + ISO code + a sample entity for testing. Eight EU jurisdictions have a CJEU C-37/20–restricted UBO register flagged with ⚠ — the agent surfaces the `alternative_url` honestly rather than substituting aggregator data.

| ISO | Country | Native registry | Sample entity |
|---|---|---|---|
| `GB` | United Kingdom | Companies House | Tesco PLC (00445790) |
| `IE` | Ireland | Companies Registration Office (CRO) | Apple Operations International Ltd (462571) |
| `FR` | France | INSEE Sirene + RNE | L'Oréal SA (552120222) |
| `DE` ⚠ | Germany | Handelsregister | Deutsche Bank AG (HRB 30000) |
| `IT` ⚠ | Italy | Registro delle imprese (via EU BRIS) | Ferrari NV |
| `ES` ⚠ | Spain | BORME (Boletín Oficial del Registro Mercantil) | Inditex SA |
| `NL` ⚠ | Netherlands | KVK Handelsregister | ASML Holding NV (33002587) |
| `BE` | Belgium | KBO/BCE (Crossroads Bank for Enterprises) | Anheuser-Busch InBev SA/NV (0417499106) |
| `PL` | Poland | KRS (Krajowy Rejestr Sądowy) | PKO Bank Polski SA (0000033057) |
| `CZ` | Czechia | ARES | ČEZ a.s. (45274649) |
| `FI` | Finland | PRH (Patentti- ja rekisterihallitus, YTJ) | Nokia Oyj (0112038-9) |
| `NO` | Norway | Brønnøysundregistrene (Enhetsregisteret) | Equinor ASA (923609016) |
| `IS` | Iceland | Fyrirtækjaskrá (Skatturinn) | Marel hf. (4202695199) |
| `CH` | Switzerland | Zefix (Federal Registry of Commerce) | Nestlé SA (CHE-105.916.057) |
| `LI` | Liechtenstein | Handelsregister Liechtenstein (Amt für Justiz) | LGT Bank AG (FL-0001.090.135-8) |
| `MC` | Monaco | RCI (Répertoire du Commerce et de l'Industrie) | Société des Bains de Mer SA |
| `IM` | Isle of Man | IoM Companies Registry | (any IoM 2006 Act company) |
| `CY` | Cyprus | DRCOR (Department of Registrar of Companies) | Bank of Cyprus PCL (HE190) |
| `KR` | South Korea | OPENDART (FSS Electronic Disclosure System) | Samsung Electronics (00126380) |
| `TW` | Taiwan | GCIS (Ministry of Economic Affairs) | TSMC (22099131) |
| `HK` | Hong Kong SAR | Companies Registry | HSBC Holdings plc (HK branch) |
| `MY` | Malaysia | SSM (Suruhanjaya Syarikat Malaysia) | Maybank Bhd (199301015245) |
| `AU` | Australia | ABR (ABN Lookup) | BHP Group Limited (49004028077) |
| `NZ` | New Zealand | NZ Companies Office | Fonterra Co-operative Group Ltd (9429038949149) |
| `CA` | Canada (federal) | Corporations Canada (CBCA, ISED) | (any federal CBCA company) |
| `CA-BC` | Canada · British Columbia | OrgBook BC | (any BC Limited Company) |
| `CA-NT` | Canada · Northwest Territories | CROS-RSEL (NWT Department of Justice) | (NT-incorporated companies) |
| `MX` | Mexico | PSM (Sistema Electrónico de Publicaciones de Sociedades Mercantiles) | (any S.A. de C.V.) |
| `KY` 💳 | Cayman Islands | CIMA (Regulated Entities Register) | (paid-tier only — anon/Free → 402) |
| `RU` | Russia | ЕГРЮЛ / ЕГРИП (FNS Federal Tax Service) + ГИР БО | Сбербанк (1027700132195) |

⚠ = CJEU C-37/20-restricted UBO register (DE / ES / IT / NL plus LU / AT / MT / PT). The agent surfaces `alternative_url` for these.
💳 = paid-tier only (anonymous + Free tiers receive HTTP 402).

The full per-jurisdiction capability matrix (which tools each registry supports, native ID format, quirks) is callable at runtime — ask the agent to run `list_jurisdictions` and it will return the live matrix.

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
