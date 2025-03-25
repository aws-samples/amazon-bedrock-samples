import boto3
import pprint
import time
import pandas as pd
from botocore.client import Config
from langchain_aws.chat_models.bedrock import ChatBedrock
from langchain_aws.embeddings.bedrock import BedrockEmbeddings
from langchain_aws.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from langchain.chains import RetrievalQA
from datasets import Dataset
from ragas import evaluate

class KnowledgeBasesEvaluations:    
    def __init__(self, model_id_eval: str, model_id_generation: str, metrics: list, questions:list, ground_truth:list, KB_ID:str):
        self.model_id_eval = model_id_eval
        self.model_id_generation = model_id_eval
        self.bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
    
        self.bedrock_client = boto3.client('bedrock-runtime')
        
        self.bedrock_agent_client = boto3.client("bedrock-agent-runtime",
                                    config=self.bedrock_config)
        self.retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=KB_ID,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 10}}, 
            client=self.bedrock_agent_client)
        self.llm_for_text_generation = ChatBedrock(model_id=self.model_id_generation, client=self.bedrock_client)
        self.llm_for_evaluation = ChatBedrock(model_id=self.model_id_eval, client=self.bedrock_client)
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm_for_text_generation, 
            retriever=self.retriever, 
            return_source_documents=True)
        
        self.bedrock_embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",
                                                    client=self.bedrock_client)
        self.evaluation_results = []
        self.evaluation_metrics = metrics
        self.questions = questions
        self.ground_truth = ground_truth
        self.generated_answers = []
        self.contexts = []

    def prepare_evaluation_dataset(self):
        for query in self.questions:
            self.generated_answers.append(self.qa_chain.invoke(query)["result"])
            self.contexts.append([docs.page_content for docs in self.retriever.invoke(query)])
        # To dict
        data = {
            "question": self.questions,
            "answer": self.generated_answers,
            "contexts": self.contexts,
            "ground_truth": self.ground_truth
        }
        # Convert dict to dataset
        dataset = Dataset.from_dict(data)
        return dataset
    
    def evaluate(self):
        dataset = self.prepare_evaluation_dataset()
        self.evaluation_results = evaluate(dataset=dataset,
                                           metrics=self.evaluation_metrics,
                                           llm=self.llm_for_evaluation,
                                           embeddings=self.bedrock_embeddings)
        return self.evaluation_results.to_pandas()

    
        
    def evaluate_individual_sample(self, delay=10):
        
        dataset = self.prepare_evaluation_dataset()

        results = pd.DataFrame()
        for idx, item in enumerate(dataset):
            # Get response and context
            question = item['question']
            response = item['answer']
            contexts = item['contexts']
            ground_truth = item['ground_truth']
            
            try:
                # Evaluate
                result = evaluate(
                    dataset = dataset, 
                    metrics=self.evaluation_metrics,
                    llm=self.llm_for_evaluation,
                    embeddings=self.bedrock_embeddings,
                )
        
                results = pd.concat([results, result.to_pandas()], ignore_index=True)
                
                # Add delay to avoid rate limiting
                time.sleep(delay)
                
                # Print progress
                print(f"Evaluated {idx + 1}/{len(self.questions)}")
                print("-" * 50)
                
            except Exception as e:
                print(f"Error processing question: {question}")
                print(f"Error details: {str(e)}")
        return results

   