from typing import Dict

"""
Add prompt templates for text-based models here.

The following dict maps a `prompt_id` to a prompt template.

Supply the prompt_id in the state machine input and ensure that your CSV file
has columns for the required formatting keys (enclosed in curly braces {}) in that template.

e.g. For prompt_id=`joke_about_topic`, your input CSV must include a `topic` column in order to 
fill that key.
"""
prompt_id_to_template: Dict[str, str] = {
    'joke_about_topic': '''Tell me a joke about {topic} in less than 50 words.''',
    'sentiment_classifier': '''
        Classify the sentiment of the following text as `positive`, `negative`, or `neutral`. 
        Just give the sentiment, no preamble or explanation.
        
        Text:
        {input_text}''',
    'question_answering': '''You are an AI assistant tasked with providing accurate and justified answers to users' questions.
    
    You will be given a task, and you should respond with a chain-of-thought surrounded by <thinking> tags, then a final answer in <answer> tags.
    
    For example, given the following task:
    
    <task>
    You are given an original reference as well as a system generated reference. Your task is to judge the naturaleness of the system generated reference. If the utterance could have been produced by a native speaker output 1, else output 0. System Reference: may i ask near where? Original Reference: where do you need a hotel near?.
    </task>
    
    <thinking>
    The utterance "may i ask near where?" is not natural. 
    This utterance does not make sense grammatically.
    Thus we output 0.
    </thinking>
    
    <answer>0</answer>

    Your turn. Please respond to the following task:
    
    <task>
    {source}
    </task>
    
    '''
}
