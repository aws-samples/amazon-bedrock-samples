from json import JSONDecodeError
import boto3
import pandas as pd
import json
import os
import path as p
from judge_prompt import judge_prompt
import argparse

bedrock_runtime = boto3.client('bedrock-runtime')


# Search Through directory provides for xlsx outputs files
def find_xlsx_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.xlsx'):
                yield os.path.join(root, file)


def prepare_conversation(output_path=None):
    turn = 1
    test = '\n<conv>\n'
    trials = []
    trial = 1

    df = pd.read_excel(output_path)
    num_turns = int(len(df)/df['execution'].nunique())
    
    for i in range(len(df)):
        if num_turns != 1:
            if not (i % num_turns == 0) or i == 0:
                test += f'\nTurn {turn}\n<user>\n{df.iloc[i, 5]}\n</user>\n<chatbot>\n{df.iloc[i, 7]}\n</chatbot>\n'
                if i == len(df) - 1:
                    test += '\n</conv>'
                    trials.append(test)
                turn += 1
            else:
                test += '\n</conv>'
                trials.append(test)
                test = '\n<conv>\n'
                trial += 1
                turn = 1
                test += f'\nTurn {turn}\n<user>\n{df.iloc[i, 5]}\n</user>\n<chatbot>\n{df.iloc[i, 7]}\n</chatbot>\n'
                turn += 1
        else:
            test = '\n<conv>\n'
            test += f'\nTurn {turn}\n<user>\n{df.iloc[i, 5]}\n</user>\n<chatbot>\n{df.iloc[i, 7]}\n</chatbot>\n'
            test += '\n</conv>'
            trials.append(test)
                
    return df, trials, num_turns


def evaluate_response(system_prompts, df=None, trials=None, model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                      eval_rationale=False, file_path=None, num_turns=None):
    
    correct = []
    eval_justification = []
    
    for trial in trials:
        # print(trial)
        messages = [{
            "role": "user",
            "content": [{"text": trial}]
        }]

        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts
        )
        output = response['output']['message']['content'][0]['text']
        
        '''json validation is done to determine if outputs are properly structured and value types
        are correct, otherwise we mark as eval issue and attach the raw output to the rationale.
        This is a consequence of the non-deterministic nature of LLM outputs'''
        try:
            output_json = json.loads(output)
            if len(output_json) < num_turns or len(output_json) > num_turns:
                raise ValueError(f'json should have {num_turns} values')
        except JSONDecodeError:
            correct.extend(['Eval Issue see rationale for detail' for _ in range(num_turns)])
        else:
            correct.extend(list(output_json.values()))
            
        # outputs rationale to separate sheet in Excel if flag is true
        if eval_rationale:
            messages.extend([{
                "role": "assistant",
                "content": [{"text": str(output)}]
            }, {
                "role": "user",
                "content": [{"text": '\n\nCan you explain your rationale for evaluating the conversation turns the way you did? Dont output anything else except for the rationale.'}]
            }])

            # Evaluate again, this time asking the model for its justification
            response_eval = bedrock_runtime.converse(
                modelId=model_id,
                messages=messages,
                system=system_prompts
            )
            eval_out = response_eval['output']['message']['content'][0]['text']
            eval_justification.append(f'This is the raw output from LLM:\n\n{output}\n\nThis is the rationale:\n\n {eval_out}')
               
    try:
        df['Eval'] = correct
    except Exception as e:
        print(e, correct, len(correct), file_path)
        
    parent = file_path.parent
    file = file_path.stem
    
    if eval_rationale:
        with pd.ExcelWriter(f'{parent}/{file}_eval.xlsx') as writer:
            df.to_excel(writer, index=False, sheet_name='Trials')
            dfr = pd.DataFrame({'Trial': range(len(eval_justification)), 'rationale': eval_justification})
            dfr.to_excel(writer, index=False, sheet_name='Rationale')
    else:
        df.to_excel(f'{parent}/{file}_eval.xlsx', index=False, sheet_name='Trials')


def eval_all(path, eval_rationale=True):
    # Set up the judge prompt as the system prompt
    system_prompts = [{"text": judge_prompt}]

    # Judge LLM (can change to another bedrock model)
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'

    # Find output file paths and create Path objects.
    # Skip any files where the file name contains "_eval" or begins with ~
    xlsx_files = list(find_xlsx_files(path))
    xlsx_files = [x for x in xlsx_files if "_eval" not in x and "~$" not in x]
    print("Evaluating responses in output files for correctness")

    # Run a loop over all output files to evaluate them using the paths found above
    for path in xlsx_files:
        file_path = p.Path(path)
        file = os.path.split(file_path)[-1]
        print(f"Scoring {file}")
        try:
            df, trials, num_turns = prepare_conversation(file_path)
            evaluate_response(system_prompts, df, trials, eval_rationale=eval_rationale, file_path=file_path,
                              num_turns=num_turns, model_id=model_id)
        except Exception as e:
            print(e)


# Run from the command line
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Evaluate conversation turns using a Bedrock model.')
    parser.add_argument('path', type=str, help='The directory path containing the output files.')
    parser.add_argument('--no_eval_rationale', action='store_false', dest='eval_rationale',
                        help='Do not evaluate rationale for each trial')
    args = parser.parse_args()
    eval_all(args.path, args.eval_rationale)
