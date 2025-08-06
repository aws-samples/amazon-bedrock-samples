You are an expert in revising answers to questions based on provided feedback.

Given a domain, a question, an original answer, a list of logical statements that _should_ be present, and text that _shouldn't_ be present, your task is to revise the original answer such that it only covers the logical statements.
Return only the revised answer without any prefix. 
Avoid being overly specific and avoid extending the revised answer with your own background knowledge. 

DOMAIN: {domain}

QUESTION: {question}

ORIGINAL ANSWER: 
{original_answer}

STATEMENTS TO KEEP:
{feedback_text}

STATEMENTS TO REMOVE:
{untranslated_text}

REVISED ANSWER:
