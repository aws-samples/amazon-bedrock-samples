You are an expert helping answer this question:

{{original_prompt}}

A formal logic verification system deemed your original answer to the question satisfiable - meaning it's incomplete and could be either valid or invalid. Below we include your original response and any up answers the user provided to your follow-up questions

{{original_response}}

{{context_augmentation}}

{{policy_context}}

Below is the feedback from this logical verification system. The feedback is structured as a list of findings. Findings include premises and claims - the translation to formal logic of the user question and your original answer. The feedback also includes a claimsTrue and claimsFalse scenarios that show the unstated assumptions that could make your answer completely valid or invalid. 

**Important**: The scenarios shown below display only the variables that have different values between the two scenarios. These disagreing variables represent the specific unstated assumptions causing the ambiguity in your answer. Focus on these variables to understand what information is missing.

Context: The answer depends on additional details. Here are the scenarios showing the disagreeing variables:

{{findings}}

You have two options for how to proceed:

**Option 1: Rewrite your answer**
If you can resolve the incompleteness by making explicit assumptions about the disagreeing variables, choose to rewrite. State all assumptions explicitly in your regenerated response.

**Option 2: Ask follow-up questions**
If you need more information to give a definitive answer, ask follow-up questions about the disagreeing variables shown above. Focus your questions on resolving the specific differences between the scenarios.

## Response Format

You MUST indicate your decision using one of these two formats:

### If you choose to REWRITE:
```
DECISION: REWRITE

[Your rewritten answer here - provide a clear, definitive yes/no answer. Keep it short and concise - a few sentences maximum. Answer naturally as if this is your first response. Never mention that you received feedback to adjust the answer. **Critical**: State all assumptions explicitly about the disagreeing variables.]
```

### If you choose to ASK_QUESTIONS:
```
DECISION: ASK_QUESTIONS

QUESTION: To give you a correct answer, I need some clarifications. Is your homework type a mathematical solution or a written response?
QUESTION: [Additional questions about specific disagreeing variables]
```

You can ask up to 5 questions. Each question must be on its own line starting with "QUESTION:". **Critical**: Only ask follow-up questions about the specific disagreeing variables shown in the scenarios above. If you ask questions, the user will provide answers before you continue.

**When you receive answers to your follow-up questions, incorporate those answers as explicit assumptions in your final response.** Make it clear in your answer what information you learned from the user and how it affects your conclusion.