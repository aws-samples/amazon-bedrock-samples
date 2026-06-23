import gradio as gr
import os
import json
import boto3
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Import the necessary classes from the module
from bedrock_ctxt_retrieval import BedrockKnowledgeBaseManager, ResponseFormatter, ChunkingStrategySelector

# Global variables to track state
kb_manager = None
formatter = None
kb_ids = {}
kb_names = {}

def initialize_system() -> str:
    """Initialize the BedrockKnowledgeBaseManager with default settings."""
    global kb_manager, formatter
    try:
        kb_manager = BedrockKnowledgeBaseManager()
        formatter = ResponseFormatter()
        return f"System initialized successfully in region: {kb_manager.region}"
    except Exception as e:
        return f"Error initializing system: {str(e)}"

def setup_knowledge_bases(chunking_strategy: str) -> str:
    """Set up knowledge bases based on selected chunking strategy."""
    global kb_manager, kb_ids, kb_names
    
    if not kb_manager:
        return "Please initialize the system first."
    
    try:
        # Check if lambda function file exists and create a copy with the expected name
        lambda_source_file = "lambda_custom_chunking_function.py"
        lambda_target_file = "lambda_function.py"
        
        # Create a copy of the lambda file with the expected name if CUSTOM or BOTH is selected
        if chunking_strategy in ["CUSTOM", "BOTH"]:
            if os.path.exists(lambda_source_file):
                with open(lambda_source_file, 'r') as source:
                    content = source.read()
                    with open(lambda_target_file, 'w') as target:
                        target.write(content)
            else:
                # Create a simple lambda function if the source doesn't exist
                with open(lambda_target_file, 'w') as f:
                    f.write("""
import json

def lambda_handler(event, context):
    # Simple custom chunking function
    chunks = []
    text = event.get('text', '')
    
    # Split by paragraphs and create chunks
    paragraphs = text.split('\\n\\n')
    for i, para in enumerate(paragraphs):
        if para.strip():
            chunks.append({
                'text': para.strip(),
                'metadata': {'chunk_id': i, 'source': 'custom_chunking'}
            })
    
    return {
        'statusCode': 200,
        'chunks': chunks
    }
""")
        
        # Base names for resources
        kb_base_name = 'kb'
        kb_description = "Knowledge Base containing complex PDF."
        results = []
        
        # Create standard knowledge base if selected
        if chunking_strategy in ["FIXED_SIZE", "BOTH"]:
            kb_name_standard = f"standard-{kb_base_name}"
            kb_id_standard = kb_manager.create_knowledge_base(
                kb_name=kb_name_standard,
                kb_description=kb_description,
                chunking_strategy="FIXED_SIZE"
            )
            kb_ids["standard"] = kb_id_standard
            kb_names["standard"] = kb_name_standard
            results.append(f"Standard KB ID: {kb_id_standard}")
        
        # Create custom chunking knowledge base if selected
        if chunking_strategy in ["CUSTOM", "BOTH"]:
            kb_name_custom = f"custom-{kb_base_name}"
            intermediate_bucket_name = f"{kb_name_custom}-intermediate-{kb_manager.timestamp_suffix}"
            lambda_function_name = f"{kb_name_custom}-lambda-{kb_manager.timestamp_suffix}"
            
            kb_id_custom = kb_manager.create_knowledge_base(
                kb_name=kb_name_custom,
                kb_description=kb_description,
                chunking_strategy="CUSTOM",
                lambda_function_name=lambda_function_name,
                intermediate_bucket_name=intermediate_bucket_name
            )
            kb_ids["custom"] = kb_id_custom
            kb_names["custom"] = kb_name_custom
            results.append(f"Custom KB ID: {kb_id_custom}")
        
        return f"Knowledge bases created successfully.\n" + "\n".join(results)
    except Exception as e:
        return f"Error creating knowledge bases: {str(e)}"

def upload_directory(directory_path: str) -> str:
    """Upload files from a directory to knowledge base buckets."""
    global kb_manager, kb_names
    
    if not kb_manager:
        return "Please initialize the system first."
    
    if not kb_names:
        return "Please set up knowledge bases first."
    
    try:
        results = []
        for kb_type, kb_name in kb_names.items():
            bucket_name = f'{kb_name}-{kb_manager.timestamp_suffix}'
            kb_manager.upload_directory_to_s3(directory_path, bucket_name)
            results.append(f"Files uploaded to {kb_type} bucket: {bucket_name}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error uploading files: {str(e)}"

def start_ingestion_jobs() -> str:
    """Start ingestion jobs for all knowledge bases."""
    global kb_manager, kb_names
    
    if not kb_manager:
        return "Please initialize the system first."
    
    if not kb_names:
        return "Please set up knowledge bases first."
    
    try:
        results = []
        for kb_type, kb_name in kb_names.items():
            kb_manager.start_ingestion_job(kb_name)
            results.append(f"Ingestion job started for {kb_type} knowledge base: {kb_name}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error starting ingestion jobs: {str(e)}"

def query_knowledge_base(kb_type: str, query_text: str, num_results: int) -> Tuple[str, str]:
    """Query the knowledge base using retrieve and generate."""
    global kb_manager, kb_ids
    
    if not kb_manager:
        return "Please initialize the system first.", ""
    
    if not kb_ids or kb_type not in kb_ids:
        return f"Knowledge base {kb_type} not found.", ""
    
    try:
        # Get the KB ID
        kb_id = kb_ids[kb_type]
        
        # Perform retrieve and generate
        response = kb_manager.retrieve_and_generate(kb_id, query_text, num_results)
        
        # Format the response
        answer = response['output']['text']
        
        # Format citations
        citations = ""
        if 'citations' in response and response['citations']:
            response_refs = response['citations'][0]['retrievedReferences']
            citations = f"Citations ({len(response_refs)}):\n\n"
            for num, chunk in enumerate(response_refs, 1):
                citations += f"Chunk {num}: {chunk['content']['text']}\n"
                citations += f"Location: {chunk['location']}\n"
                if 'metadata' in chunk:
                    citations += f"Metadata: {chunk['metadata']}\n"
                citations += "\n"
        
        return answer, citations
    except Exception as e:
        return f"Error querying knowledge base: {str(e)}", ""

def retrieve_only(kb_type: str, query_text: str, num_results: int) -> str:
    """Perform a retrieve operation using the knowledge base."""
    global kb_manager, kb_ids
    
    if not kb_manager:
        return "Please initialize the system first."
    
    if not kb_ids or kb_type not in kb_ids:
        return f"Knowledge base {kb_type} not found."
    
    try:
        # Get the KB ID
        kb_id = kb_ids[kb_type]
        
        # Perform retrieve operation
        response = kb_manager.retrieve(kb_id, query_text, num_results)
        
        # Format the results
        results = response.get('retrievalResults', [])
        output = f"Retrieved {len(results)} results:\n\n"
        
        for num, chunk in enumerate(results, 1):
            output += f"Chunk {num}: {chunk['content']['text']}\n"
            output += f"Location: {chunk['location']}\n"
            output += f"Score: {chunk['score']}\n"
            if 'metadata' in chunk:
                output += f"Metadata: {chunk['metadata']}\n"
            output += "\n"
        
        return output
    except Exception as e:
        return f"Error retrieving from knowledge base: {str(e)}"

def run_ragas_evaluation(questions: List[str], ground_truths: List[str]) -> str:
    """Run RAGAS evaluation on the knowledge bases."""
    global kb_manager, kb_ids
    
    if not kb_manager:
        return "Please initialize the system first."
    
    if len(kb_ids) < 2 or "standard" not in kb_ids or "custom" not in kb_ids:
        return "Both standard and custom knowledge bases are required for evaluation."
    
    try:
        # Import the RAG evaluator
        try:
            from rag_evaluator import RAGEvaluator
        except ImportError:
            return "RAG evaluator module not found. Please ensure it's available in the path."
        
        # Create a Bedrock runtime client with appropriate configuration
        bedrock_runtime_client = boto3.client(
            'bedrock-runtime',
            region_name=kb_manager.region,
            config=boto3.session.Config(
                read_timeout=900,  # 15 minutes
                connect_timeout=60,
                retries={'max_attempts': 3}
            )
        )
        
        # Initialize the RAG evaluator
        evaluator = RAGEvaluator(
            bedrock_runtime_client=bedrock_runtime_client,
            bedrock_agent_runtime_client=kb_manager.bedrock_agent_runtime_client
        )
        
        # Compare knowledge base strategies
        kb_strategy_map = {
            "Default Chunking": kb_ids["standard"],
            "Contextual Chunking": kb_ids["custom"]
        }
        
        # Run the evaluation
        comparison_df = evaluator.compare_kb_strategies(kb_strategy_map, questions, ground_truths)
        
        # Format and save the results
        styled_df = evaluator.format_comparison(comparison_df)
        comparison_df.to_csv("ragas_evaluation_results.csv")
        
        return f"RAGAS Evaluation completed. Results saved to ragas_evaluation_results.csv\n\n{styled_df.to_string()}"
    except Exception as e:
        return f"Error running RAGAS evaluation: {str(e)}"

def delete_all_resources() -> str:
    """Delete all knowledge bases and associated resources."""
    global kb_manager, kb_ids, kb_names
    
    if not kb_manager:
        return "Please initialize the system first."
    
    if not kb_names:
        return "No knowledge bases to delete."
    
    try:
        results = []
        for kb_type, kb_name in list(kb_names.items()):
            kb_manager.delete_knowledge_base(
                kb_name,
                delete_s3_bucket=True,
                delete_iam_roles_and_policies=True,
                delete_lambda_function=(kb_type == "custom")
            )
            results.append(f"Knowledge base {kb_name} deleted successfully.")
            
            # Remove from tracking dictionaries
            if kb_name in kb_ids:
                del kb_ids[kb_name]
            del kb_names[kb_type]
        
        return "\n".join(results)
    except Exception as e:
        return f"Error deleting resources: {str(e)}"

# Create the Gradio interface
with gr.Blocks(title="Bedrock Knowledge Base Manager") as app:
    gr.Markdown("# AWS Bedrock Knowledge Base Manager")
    
    with gr.Tab("Setup"):
        with gr.Row():
            init_button = gr.Button("Initialize System")
        
        with gr.Row():
            chunking_strategy = gr.Radio(
                ["FIXED_SIZE", "CUSTOM", "BOTH"], 
                label="Chunking Strategy", 
                value="FIXED_SIZE",
                info="Select the chunking strategy for your knowledge base(s)"
            )
            setup_button = gr.Button("Setup Knowledge Bases")
        
        with gr.Row():
            dir_path = gr.Textbox(label="Data Directory Path", value="synthetic_dataset")
            upload_button = gr.Button("Upload Data")
        
        setup_output = gr.Textbox(label="Setup Status", lines=5)
        
        init_button.click(initialize_system, outputs=setup_output)
        setup_button.click(setup_knowledge_bases, inputs=[chunking_strategy], outputs=setup_output)
        upload_button.click(upload_directory, inputs=[dir_path], outputs=setup_output)
    
    with gr.Tab("Start Ingestion"):
        ingest_button = gr.Button("Start Ingestion Jobs")
        ingest_output = gr.Textbox(label="Ingestion Status", lines=3)
        ingest_button.click(start_ingestion_jobs, outputs=ingest_output)
    
    with gr.Tab("Query Knowledge Base"):
        available_kb_types = gr.Dropdown(
            choices=["standard", "custom"],
            label="Knowledge Base Type",
            value="standard",
            interactive=True
        )
        
        with gr.Row():
            query_text = gr.Textbox(label="Query")
            query_num_results = gr.Slider(
                minimum=1, 
                maximum=10, 
                value=5, 
                step=1, 
                label="Number of Results"
            )
        
        with gr.Row():
            query_button = gr.Button("Query (Retrieve and Generate)")
            retrieve_button = gr.Button("Retrieve Only")
        
        with gr.Row():
            query_answer = gr.Textbox(label="Answer", lines=10)
            query_citations = gr.Textbox(label="Citations", lines=10)
        
        retrieve_output = gr.Textbox(label="Retrieved Results", lines=15)
        
        query_button.click(
            query_knowledge_base, 
            inputs=[available_kb_types, query_text, query_num_results], 
            outputs=[query_answer, query_citations]
        )
        
        retrieve_button.click(
            retrieve_only, 
            inputs=[available_kb_types, query_text, query_num_results], 
            outputs=retrieve_output
        )
    
    with gr.Tab("RAGAS Evaluation"):
        gr.Markdown("### Run RAGAS Evaluation on Knowledge Bases")
        
        with gr.Row():
            eval_questions = gr.Textbox(
                label="Evaluation Questions (one per line)",
                lines=5,
                value="What was the primary reason for the increase in net cash provided by operating activities for Octank Financial in 2021?\nIn which year did Octank Financial have the highest net cash used in investing activities, and what was the primary reason for this?\nWhat was the primary source of cash inflows from financing activities for Octank Financial in 2021?\nBased on the information provided, what can you infer about Octank Financial's overall financial health and growth prospects?"
            )
            
            eval_ground_truths = gr.Textbox(
                label="Ground Truths (one per line)",
                lines=5,
                value="The increase in net cash provided by operating activities was primarily due to an increase in net income and favorable changes in operating assets and liabilities.\nOctank Financial had the highest net cash used in investing activities in 2021, at $360 million. The primary reason for this was an increase in purchases of property, plant, and equipment and marketable securities\nThe primary source of cash inflows from financing activities for Octank Financial in 2021 was an increase in proceeds from the issuance of common stock and long-term debt.\nBased on the information provided, Octank Financial appears to be in a healthy financial position and has good growth prospects. The company has consistently increased its net cash provided by operating activities, indicating strong profitability and efficient management of working capital. Additionally, Octank Financial has been investing in long-term assets, such as property, plant, and equipment, and marketable securities, which suggests plans for future growth and expansion. The company has also been able to finance its growth through the issuance of common stock and long-term debt, indicating confidence from investors and lenders. Overall, Octank Financial's steady increase in cash and cash equivalents over the past three years provides a strong foundation for future growth and investment opportunities."
            )
        
        eval_button = gr.Button("Run RAGAS Evaluation")
        eval_output = gr.Textbox(label="Evaluation Results", lines=20)
        
        eval_button.click(
            run_ragas_evaluation,
            inputs=[eval_questions, eval_ground_truths],
            outputs=eval_output
        )
    
    with gr.Tab("Manage Resources"):
        delete_button = gr.Button("Delete All Resources")
        delete_output = gr.Textbox(label="Deletion Status", lines=3)
        delete_button.click(delete_all_resources, outputs=delete_output)

if __name__ == "__main__":
    app.launch()