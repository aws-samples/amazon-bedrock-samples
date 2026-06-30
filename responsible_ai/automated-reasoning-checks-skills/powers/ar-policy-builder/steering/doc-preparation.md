# Preparing a Source Document for AR Extraction

The quality of your policy depends directly on the quality of the source document.

## Clear vs. vague rules
AR extracts best from documents where each rule states a **condition and an outcome**.

| Clear (good) | Vague (poor) |
|---|---|
| "Full-time employees with at least 12 months of continuous service are eligible for parental leave." | "Eligible employees may apply for parental leave subject to manager approval." |
| "Refund requests must be submitted within 30 days of purchase. Items must be in original packaging." | "Refunds are handled on a case-by-case basis." |

## Size limits & splitting
- **≤ 5 MB and ≤ 50,000 characters** (images and tables count toward the character limit).
- If larger or multi-domain, **split into focused sections** (leave / benefits / expenses) and build the
  first section, then merge the rest with iterative building (`build_from_document.py --merge`).

## Pre-process complex documents
Remove headers/footers/TOC/appendices and boilerplate/legal disclaimers that don't contain rules.
They produce noisy policies with unnecessary variables. Simplify complex tables into plain-text statements.

## (Optional) LLM rule extraction
For narrative/legal prose, use `scripts/extract_rules_with_llm.py` to rewrite the doc as if-then rules
first. Review:
- `confidence: low` rules: verify against the source.
- `ruleType: implicit` rules: these were inferred, not stated, so confirm intent.
- the `ambiguities` array: source areas that are unclear and may need rewriting.
**Always review LLM output against the original before using it as AR source text.**

## Write effective build `instructions`
Cover three things:
1. **The use case**: "This policy validates an HR chatbot answering leave-eligibility questions."
2. **Example user questions**: "Users ask 'Am I eligible for parental leave if I've worked here 9 months?'"
3. **Focus**: "Focus on sections 3–5 (leave policies). Ignore the company overview in section 1."
