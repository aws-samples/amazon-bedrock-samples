# rag_evaluator.py
import time
import boto3
import pandas as pd
from typing import List, Dict, Any, Optional

# Import RAGAS components
from ragas import SingleTurnSample, EvaluationDataset
from ragas import evaluate
from ragas.metrics import (
    context_recall,
    context_precision,
    answer_correctness
)

class RAGEvaluator:
    """
    A class to evaluate RAG (Retrieval-Augmented Generation) systems using the RAGAS framework.
    """
    
    def __init__(self, 
                bedrock_runtime_client,
                bedrock_agent_runtime_client,
                text_generation_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
                evaluation_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
                embedding_model_id: str = "amazon.titan-embed-text-v2:0"):
        """
        Initialize the RAG evaluator with AWS clients and model IDs.
        
        Args:
            bedrock_runtime_client: Boto3 client for Bedrock runtime
            bedrock_agent_runtime_client: Boto3 client for Bedrock agent runtime
            text_generation_model_id: Model ID for text generation
            evaluation_model_id: Model ID for evaluation
            embedding_model_id: Model ID for embeddings
        """
        self.bedrock_runtime_client = bedrock_runtime_client
        self.bedrock_agent_runtime_client = bedrock_agent_runtime_client
        self.text_generation_model_id = text_generation_model_id
        self.evaluation_model_id = evaluation_model_id
        self.embedding_model_id = embedding_model_id
        
        # Import LangChain components here to avoid circular imports
        from langchain_aws import ChatBedrock
        from langchain_aws import BedrockEmbeddings
        
        # Initialize LangChain components
        self.llm_for_evaluation = ChatBedrock(
            model_id=evaluation_model_id, 
            client=bedrock_runtime_client
        )
        self.bedrock_embeddings = BedrockEmbeddings(
            model_id=embedding_model_id, 
            client=bedrock_runtime_client
        )
        
        # Define metrics for evaluation
        self.metrics = [
            context_recall,
            context_precision,
            answer_correctness
        ]
    
    def retrieve_and_generate(self, query: str, kb_id: str) -> Dict[str, Any]:
        """
        Perform a retrieve and generate operation using the knowledge base.
        
        Args:
            query: Query text
            kb_id: Knowledge base ID
            
        Returns:
            Response from the retrieve and generate operation
        """
        start = time.time()
        response = self.bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id,
                    'modelArn': self.text_generation_model_id
                }
            }
        )
        time_spent = time.time() - start
        print(f"[Response]\n{response['output']['text']}\n")
        print(f"[Invocation time]\n{time_spent}\n")

        return response
    
    def prepare_eval_dataset(self, kb_id: str, questions: List[str], ground_truths: List[str]) -> EvaluationDataset:
        """
        Prepare an evaluation dataset for RAGAS.
        
        Args:
            kb_id: Knowledge base ID
            questions: List of questions
            ground_truths: List of ground truth answers
            
        Returns:
            RAGAS evaluation dataset
        """
        # Lists to store SingleTurnSample objects
        samples = []
        
        for question, ground_truth in zip(questions, ground_truths):
            # Get response and context from your retrieval system
            response = self.retrieve_and_generate(question, kb_id)
            answer = response["output"]["text"]
            
            # Process contexts
            contexts = []
            for citation in response["citations"]:
                context_texts = [
                    ref["content"]["text"]
                    for ref in citation["retrievedReferences"]
                    if "content" in ref and "text" in ref["content"]
                ]
                contexts.extend(context_texts)
            
            # Create a SingleTurnSample
            sample = SingleTurnSample(
                user_input=question,
                retrieved_contexts=contexts,
                response=answer,
                reference=ground_truth
            )
            
            # Add the sample to our list
            samples.append(sample)
            
            # Rate limiting if needed
            # time.sleep(10)

        # Create EvaluationDataset from samples
        eval_dataset = EvaluationDataset(samples=samples)
        
        return eval_dataset
    
    def evaluate_kb(self, kb_id: str, questions: List[str], ground_truths: List[str]) -> pd.DataFrame:
        """
        Evaluate a knowledge base using RAGAS.
        
        Args:
            kb_id: Knowledge base ID
            questions: List of questions
            ground_truths: List of ground truth answers
            
        Returns:
            DataFrame with evaluation results
        """
        # Prepare evaluation dataset
        eval_dataset = self.prepare_eval_dataset(kb_id, questions, ground_truths)
        
        # Evaluate using RAGAS
        result = evaluate(
            dataset=eval_dataset,
            metrics=self.metrics,
            llm=self.llm_for_evaluation,
            embeddings=self.bedrock_embeddings,
        )
        
        # Convert to DataFrame
        result_df = result.to_pandas()
        
        return result_df
    
    def compare_kb_strategies(self, kb_ids: Dict[str, str], questions: List[str], ground_truths: List[str]) -> pd.DataFrame:
        """
        Compare multiple knowledge base strategies.
        
        Args:
            kb_ids: Dictionary mapping strategy names to knowledge base IDs
            questions: List of questions
            ground_truths: List of ground truth answers
            
        Returns:
            DataFrame comparing the strategies
        """
        results = {}
        
        # Evaluate each knowledge base
        for strategy_name, kb_id in kb_ids.items():
            print(f"\n=== Evaluating {strategy_name} strategy ===")
            result_df = self.evaluate_kb(kb_id, questions, ground_truths)
            
            # Calculate average metrics
            avg_metrics = result_df[['context_recall', 'context_precision', 'answer_correctness']].mean()
            results[strategy_name] = avg_metrics
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(results)
        
        return comparison_df
    
    def format_comparison(self, comparison_df: pd.DataFrame) -> pd.DataFrame:
        """
        Format the comparison DataFrame with highlighting.
        
        Args:
            comparison_df: DataFrame comparing strategies
            
        Returns:
            Styled DataFrame with highlighting
        """
        def highlight_max(s):
            is_max = s == s.max()
            return ['background-color: #90EE90' if v else '' for v in is_max]
        
        return comparison_df.style.apply(highlight_max, axis=1)
