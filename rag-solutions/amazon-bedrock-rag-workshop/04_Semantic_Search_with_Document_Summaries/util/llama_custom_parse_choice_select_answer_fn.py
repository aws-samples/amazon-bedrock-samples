from typing import Dict, List, Optional, Set, Tuple
def custom_parse_choice_select_answer_fn(
    answer: str, num_choices: int, raise_error: bool = False
) -> Tuple[List[int], Optional[List[float]]]:
    """Default parse choice select answer function."""
    #print(f"answer is {answer}")
    answer_lines = answer.split("\n")
    #print(answer_lines)
    answer_nums = []
    answer_relevances = []
    for answer_line in answer_lines:
        line_tokens = answer_line.split(",")
        #print(line_tokens)
        if len(line_tokens) != 2:
            if not raise_error:
                continue
            else:
                raise ValueError(
                    f"Invalid answer line: {answer_line}. "
                    "Answer line must be of the form: "
                    "answer_num: <int>, answer_relevance: <float>"
                )
        else:
            if (line_tokens[0].find("Doc:") > -1) and (line_tokens[1].find("Relevance:")>-1):
                
                #print(f"line token is {line_tokens[0]}")        
                answer_num = int(line_tokens[0].split(":")[1].strip())
                #print(f"answer_num is {answer_num}")
                if answer_num > num_choices:
                    continue
                answer_nums.append(answer_num)
                answer_relevances.append(float(line_tokens[1].split(":")[1].strip()))
    #print(f"{answer_nums}")
    #print(f"{answer_relevances}")
    return answer_nums, answer_relevances

answer1 = "Doc: 9, Relevance: 10\nDoc: 6, Relevance: 9\n Doc: 1, Relevance: 7\nline token is The 2019 shareholder letter (Doc 4) is also highly relevant with a score of 9."

answer2 = '''Doc: 6, Relevance: 10
Doc: 4, Relevance: 9  
Doc: 1, Relevance: 8

The 2020 shareholder letter (Doc 6) is the most relevant document to answering this question, with a relevance score of 10. It provides a high-level overview of Amazon's history and growth over the past 23 years since its IPO in 1997. The letter is written by current Amazon CEO Jeff Bezos, so it directly indicates that Bezos is the CEO.

The 2019 shareholder letter (Doc 4) is also highly relevant with a score of 9. As a letter from Bezos, it implies he is the CEO in 2019. Letters for other years like 2020 confirm he has retained this role.

Finally, the Amazon shareholder letter summary (Doc 1) has a relevance of 8. It summarizes a shareholder letter from Amazon's CEO, which provides a strong signal that the CEO is Jeff Bezos, though the content itself does not outright state this. The other documents do not directly help identify the current Amazon CEO.'''
custom_parse_choice_select_answer_fn(answer2, 10)
       
          