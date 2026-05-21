You are an expert in revising answers to questions based on provided feedback.

Given a domain, a question, an original answer, and feedback consisting of pairs of scenarios your task is to revise the original answer based on the feedback. 
Each provided scenario pair consists of one scenario which should be true and another scenario which should be false, but both scenarios are classified the same based on the original answer. 
Use these scenarios to add more detail or context to the original answer so that the revised answer can distinguish between these scenarios.
Return only the revised answer without any prefix. 
Avoid being overly specific and avoid extending the revised answer with your own background knowledge. 

DOMAIN: {domain}

QUESTION: {question}

ORIGINAL ANSWER: 
{original_answer}

TRUE AND FALSE SCENARIOS:
{true_false_scenarios_text}

REVISED ANSWER:
