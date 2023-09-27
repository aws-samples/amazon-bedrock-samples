from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from typing import List, Dict, Any
import tiktoken


class TokenCounterHandler(BaseCallbackHandler):

    MODEL_ENCODING = "gpt-3.5-turbo"
    ENCODING = tiktoken.encoding_for_model(MODEL_ENCODING)

    def __init__(self, clear_report_on_chain_start=True):
        self.tokens = 0
        self.embedding_tokens = 0
        self.prompt_tokens = 0
        self.generation_tokens = 0

    def on_retriever_start(self, query: str, **kwargs):
        numtokens = len(self.ENCODING.encode(query))
        self.tokens += numtokens
        self.embedding_tokens += numtokens


    def on_llm_start(self, serialized, prompts: List[str], **kwargs):
        for prompt in prompts:   
            numtokens = len(self.ENCODING.encode(prompt))
            self.tokens += numtokens
            self.prompt_tokens += numtokens

    def on_llm_end(self, response: LLMResult, **kwargs):
        
        for generation in response.generations:
            numtokens = len(self.ENCODING.encode(generation[0].text))
            self.tokens += numtokens
            self.generation_tokens += numtokens

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs):
        self.report()
    
    def clear_report(self):
        self.tokens = 0
        self.embedding_tokens = 0
        self.prompt_tokens = 0
        self.generation_tokens = 0

    def report(self):
        print(f"\nToken Counts:\nTotal: {self.tokens}\nEmbedding: N/A\nPrompt: {self.prompt_tokens}\nGeneration:{self.generation_tokens}\n")