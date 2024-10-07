import os
import pandas as pd
import boto3
import json
from botocore.config import Config
from claude_3 import Claude3Wrapper, invoke_claude_3_with_text
def analyze_csv_files(root_folder):
    data_context = {}

    # Walk through all directories and files in the root folder
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for file in filenames:
            if file.endswith('.csv'):
                # Construct the full file path
                file_path = os.path.join(dirpath, file)
                
                # Read the CSV file
                df = pd.read_csv(file_path)
                
                # Get column names and sample data
                columns = df.columns.tolist()
                sample_data = df.head(1).to_dict(orient='records')[0]
                
                # Use relative path from root_folder as key to handle different files with the same name in different folders
                relative_path = os.path.relpath(file_path, start=root_folder)
                
                # Store this info
                #relative_path
                data_context[relative_path.replace('.csv', '').split('/')[0].replace(' ','_')] = {
                    'columns': columns,
                    'sample_data': sample_data
                }

    return data_context

data_folder_name = "xxx"
data_folder = f'./Data/{data_folder_name}'
glue_database_name = f"{data_folder_name.lower()}"

data_context = analyze_csv_files(data_folder)
#print(data_context)

if 1==1:
    def generate_instruction(data_context, glue_database_name):
     
        instruction_parts = [
            f"You are an advanced database querying agent crafted specifically for generating precise SQL queries concerning the {glue_database_name} database. Your tasks involve creating syntactically correct AWS Athena queries tailored to specific questions. Always ensure that:",
            "1. Queries are efficient, targeting only a few relevant columns rather than extracting all data from any table.",
            "2. You utilize only those column names that are visible in the schema description to avoid referencing non-existent columns.",
            "3. You accurately identify the table each column belongs to, and",
            "4. Appropriately qualify column names with their respective table names as necessary.",
            "5. Always enclose table names and column names in DOUBLE quotes. This is super important as it is the required format for AWS Athena and helps prevent potential errors due to case sensitivity or special characters.",
            "6. For queries with filters based on categorical data first generate a sample a SQL query (using distinct) against relevant tables to familiarize yourself with the content of a particular column"
            f"7. After reviewing the schema of the entire {glue_database_name} and the columns of the tables, decide on your final SQL query to answer the question. Remember, to answer a question thoroughly (or provide AWS S3 link of response), you might need to perform joins between tables. Your final SQL query requires a deep understanding of the relationships within the database to construct effective and accurate queries.",
            "The following examples illustrate the kind of queries you should be able to construct based on the available data:"
        ]

        
        for file, context in data_context.items():
            #table_name = file.replace('.csv', '').split('/')[0]
            table_name = file
            columns = ', '.join([f'"{col}"' for col in context['columns'] if ' ' in col or not col.isidentifier()])
            sample_query = f"SELECT \"{columns}\" FROM \"{table_name}\" LIMIT 5;"
            instruction_parts.append(f"- Table `{table_name}` example query: {sample_query}")
        
        return ' '.join(instruction_parts)

    instruction_text = generate_instruction(data_context, glue_database_name)
    #print(instruction_text)


    # question = f"""
    # Please craft a comprehensive instruction UP TO 1200 WORDS (this is a hard constraint max Length should be lower than 1200 words) for the Bedrock agent (Instructions that tell the agent what it should do and how it should interact with users). Your instruction must be based on ALL 7 CONTEXTUAL DETAILS provided to develop this instruction text. The final submission should consist solely of your detailed instruction without saying for example "here is your...\n
    
    # {instruction_text}.
    
    # """
    question = f"""
    Craft a comprehensive and cohesive instruction in one full paragraph for the Bedrock agent, with a Maximum length of 1200 characters (1200 characters is hard limit so adhere to this limit on generating text). These instructions should clearly outline the agent's tasks and how it should interact with users. Ensure that your instruction is based on all seven contextual details provided. The final answer should be concise, detailed and precise, without any introductory phrases such as "Here is your...".

    Contextual details:
    {instruction_text}
    """



    # Invoke Claude 3 with a text prompt
    text_prompt = question
   

    instruction=invoke_claude_3_with_text(question)


    #print(text_prompt)
    #print("\n \n here is instruction \n \n")
    #print(instruction)