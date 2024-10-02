import boto3
import pandas as pd
import json
import os
import path as p
from pydantic import BaseModel, Field, field_validator
from typing import Dict,Union
from judge_prompt import judge_prompt

bed_run=boto3.client('bedrock-runtime')

# Search Through directory provides for xlsx outputs files
def find_xlsx_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.xlsx'):
                yield os.path.join(root, file)

def prepare_conv(output_path=None):
    turn=1
    test='\n<conv>\n'
    trials=[]
    trial=1
    
    try:
        df=pd.read_excel(output_path)
    except Exception as e:
        print(e)
        
    num_turns=int(len(df)/df['execution'].nunique())
    
    for i in range(len(df)):

            if num_turns!=1:

                if not (i%num_turns==0) or i==0:
                    test+=(f'\nTurn {turn}\n<user>\n{df.iloc[i,5]}\n</user>\n<chatbot>\n{df.iloc[i,7]}\n</chatbot>\n')
                    if i==len(df)-1:
                         test+='\n</conv>'
                         trials.append(test)
                    turn+=1
                else:   
                    test+='\n</conv>'
                    trials.append(test)
                    test='\n<conv>\n'
                    trial+=1
                    turn=1
                    test+=(f'\nTurn {turn}\n<user>\n{df.iloc[i,5]}\n</user>\n<chatbot>\n{df.iloc[i,7]}\n</chatbot>\n')
                    turn+=1
            else:
                test='\n<conv>\n'
                test+=(f'\nTurn {turn}\n<user>\n{df.iloc[i,5]}\n</user>\n<chatbot>\n{df.iloc[i,7]}\n</chatbot>\n')
                test+='\n</conv>'
                trials.append(test)
                
    return df,trials,num_turns


class IntegerJsonModel(BaseModel):
    data: Dict[Union[str, int], int] = Field(...)

    @field_validator('data', mode='before')
    @classmethod
    def validate_integer_keys_and_values(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Input must be a dictionary")
        for value in v.values():
            if value not in range(1,6):
                raise ValueError(f"Value '{value}' for key '{key}' is not an integer in[1,6]")
        return v

    #optional for post-processing of validated outputs
    
    '''class Config:
        json_encoders = {
            int: lambda v: v
        }'''
    

def eval(system_prompts, df=None,trials=None,model_id='anthropic.claude-3-sonnet-20240229-v1:0',eval_rationale=False,file_path=None,num_turns=None):
    
    correct=[]
    eval_just=[]
    
    for trial in trials:
        #print(trial)
        messages = [{
            "role": "user",
            "content": [{"text": trial}]
        }]

        response = bed_run.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts
        )
        output=response['output']['message']['content'][0]['text']
        
        '''json validation is done to determine if outputs are properly structured and value types
        are correct,otherwise we mark as eval issue and attach the raw output to the rationale.
        This is a consequence of the non-deterministic nature of LLM outputs'''
        
        try:
            output_json=json.loads(output)
            IntegerJsonModel(data=output_json) 
            if(len(output_json)<num_turns or len(output_json)>num_turns):
               raise ValueError(f'json should have {num_turns} values')
        except Exception as e:
            correct.extend(['Eval Issue see rationale for detail' for _ in range(num_turns)])
        else:
            correct.extend(list(output_json.values()))
            
        #outputs rationale to seperate sheet in excel if flag is true
        if eval_rationale==True:
            messages.extend([{
            "role": "assistant",
            "content": [{"text": str(output)}]
        },{
            "role": "user",
            "content": [{"text": '\n\nCan you explain your rationale for evaluating the conversation turns the way you did? Dont output anything else except for the rationale.'}]
        }])

            response_eval = bed_run.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts
        )
            eval_out=response_eval['output']['message']['content'][0]['text']
            eval_just.append(f'This is the raw output from LLM:\n\n{output}\n\nThis is the rationale:\n\n {eval_out}')
               
    try:
        df['Eval']=correct
    except exception as e:
        print(e,correct,len(correct),file_path)
        
    parent=file_path.parent
    file=file_path.stem
    
    if eval_rationale==True:
        with pd.ExcelWriter(f'{parent}/{file}_eval.xlsx') as writer:
            df.to_excel(writer,index=False,sheet_name='Trials')
            dfr=pd.DataFrame({'Trial':range(len(eval_just)),'rationale':eval_just})
            dfr.to_excel(writer,index=False,sheet_name='Rationale')
    else:
        df.to_excel(f'{parent}/{file}_eval.xlsx', index=False,sheet_name='Trials')
        
def eval_all(path):
    # Setup the judge prompt as system prompt
    system_prompts = [{"text": judge_prompt}]

    #Judge LLM (can change to another bedrock model)
    model_id='anthropic.claude-3-sonnet-20240229-v1:0'

    # Find output file paths and create Path objects 
    xlsx_files = list(find_xlsx_files(path))
    file_paths=[p.Path(x) for x in xlsx_files]

    #verify paths
    for file in xlsx_files:
        print(file)

    # run a loop over all output files to evaluate them using the paths found above

    for file in file_paths:
        df,trials,num_turns=prepare_conv(file)
        eval(system_prompts, df,trials,eval_rationale=True,file_path=file,num_turns=num_turns)