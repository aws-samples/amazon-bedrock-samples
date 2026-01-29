You are an expert helping answer this question:

{{original_prompt}}

A formal logic verification system deemed your original answer to the question ambiguous - meaning either the user question or your answer could be interpreted in different ways. Below we include your original response and any up answers the user provided to your follow-up questions

{{original_response}}

{{context_augmentation}}

{{policy_context}}

Below is the feedback from this logical verification system. The feedback is structured as a list of findings. Findings include alternative interpretations of the user question and generated text in formal logic. Use the alternative interpretations to disambiguate if the issue is in your generated content, or ask follow up questions to the user if the ambiguity is in the user question. If one of the interpretations suggests there are multiple, discordant findings in the text you generated, simplify your answer to only make the necessary statement.

{{findings}}

You have two options for how to proceed:

**Option 1: Rewrite your answer**
If you can resolve the ambiguity by making a reasonable assumption or clarifying your response, choose to rewrite. Use this when the ambiguity is in how you expressed your answer, not in the user's question itself.

**Option 2: Ask follow-up questions**
If additional information from the user would help you deliver an unambiguous answer based on the feedback, ask follow-up questions. This is the preferred option when the user's question itself is ambiguous or when the feedback reveals multiple valid interpretations of what the user is asking. Asking clarifying questions demonstrates expertise and ensures you provide the most accurate answer.

## Response Format

You MUST indicate your decision using one of these two formats:

### If you choose to REWRITE:
```
DECISION: REWRITE

[Your rewritten answer here - provide a clear, definitive yes/no answer. Keep it short and concise - a few sentences maximum. Answer naturally as if this is your first response. Never mention that you received feedback to adjust the answer.]
```

### If you choose to ASK_QUESTIONS:
```
DECISION: ASK_QUESTIONS

QUESTION: Are you referring to a mathematical solution or essay?
QUESTION: Are you asking about scenario A or scenario B?
```

You can ask up to 5 questions. Each question must be on its own line starting with "QUESTION:". If you ask questions, the user will provide answers before you continue.