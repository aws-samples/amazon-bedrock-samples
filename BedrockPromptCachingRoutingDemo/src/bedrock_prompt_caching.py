"""
Bedrock Prompt Caching CLI Application

This module provides a class-based implementation for interacting with Amazon Bedrock
with prompt caching capabilities and a CLI interface for user interaction.
"""

# Standard libraries
import json
import time
import os
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Data processing and visualization
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import seaborn as sns

# AWS and external services
import requests

# Local imports
from file_processor import FileProcessor # For processing different file types
from bedrock_service import BedrockService # For interacting with Bedrock services
from model_manager import ModelManager # For managing Bedrock models

# Cache mode constants for controlling prompt caching behavior
class CACHE(str, Enum):
    """Enumeration of cache modes for Bedrock prompt caching"""
    ON = "ON" # Enable caching with checkpoint
    OFF = "OFF" # Disable caching completely
    READ = "READ" # Cache hit - reading from cache
    WRITE = "WRITE" # Cache miss - writing to cache
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

class CacheManager:
    """Manages the caching of responses
    
    This class provides in-memory caching for Bedrock responses.
    """
    
    def __init__(self):
        """Initialize cache manager"""
        self.cache_store = {} # Store cache information by cache key
    
    def store_cache_info(self, cache_key: str, is_cache_hit: bool, document: str, query: str, metrics: Dict, turn: int = 0) -> None:
        """Store detailed cache information for analysis
        
        Args:
            cache_key: The unique cache key
            is_cache_hit: Whether this was a cache hit
            document: The document content
            query: The user's question
            metrics: Usage metrics from the API response
            turn: The conversation turn number (default: 0)
        """
        # Handle different key formats in the metrics dictionary
        cache_read_tokens = (
            metrics.get("cache_read_input_tokens", 0) or 
            metrics.get("cacheReadInputTokens", 0)
        )
        
        cache_creation_tokens = (
            metrics.get("cache_creation_input_tokens", 0) or 
            metrics.get("cacheCreationInputTokens", 0)
        )
        
        input_tokens = metrics.get("inputTokens", 0)
        output_tokens = metrics.get("outputTokens", 0)
        
        self.cache_store[cache_key] = {
            "cache_key": cache_key,
            "is_cache_hit": is_cache_hit,
            "cached_content": document if turn == 0 else "",
            "question": query,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_read_tokens": cache_read_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "invocation_latency": metrics.get("response_time_seconds", 0),
            "turn": turn + 1
        }
    
    def get_cache_summary(self, cache_key: str) -> str:
        """Get a formatted summary of cache information for a specific key
        
        Args:
            cache_key: The cache key to get information for
            
        Returns:
            Formatted string with cache summary
        """
        if cache_key not in self.cache_store:
            return "No cache information available for this query."
            
        cache_info = self.cache_store[cache_key]
        is_cache_hit = cache_info["is_cache_hit"]
        
        # Calculate performance metrics
        input_tokens = cache_info.get("input_tokens", 0)
        input_tokens_cache_read = cache_info.get("cache_read_tokens", 0)
        input_tokens_cache_create = cache_info.get("cache_creation_tokens", 0)
        invocation_latency = cache_info.get("invocation_latency", 0)
        
        # For cache hits, if cache_read_tokens is still 0, use input_tokens
        if is_cache_hit and input_tokens_cache_read == 0 and input_tokens > 0:
            input_tokens_cache_read = input_tokens
            
        total_input_tokens = input_tokens + input_tokens_cache_read
        percentage_cached = (input_tokens_cache_read / total_input_tokens * 100) if total_input_tokens > 0 else 0
        
        # Calculate estimated cost savings (assuming $0.01 per 1K tokens)
        token_cost_per_k = 0.01
        estimated_savings = (input_tokens_cache_read / 1000) * token_cost_per_k
        
        # Calculate latency benefit (assuming average response time of 2 seconds without cache)
        avg_response_time = 2.0
        latency_benefit = ((avg_response_time - invocation_latency) / avg_response_time * 100) if invocation_latency > 0 else 0
        
        summary = ["\n📊 Cache Summary:"]
        summary.append(f" Cache key: {cache_key}")
        
        if is_cache_hit:
            summary.append(f" ✅ CACHE HIT")
            summary.append(f" Cache read tokens: {input_tokens_cache_read}")
            summary.append(f" Input tokens saved: {input_tokens_cache_read}")
            summary.append(f" {percentage_cached:.1f}% of input prompt cached ({total_input_tokens} tokens)")
            
            # Add cost and latency benefits
            summary.append(f" Estimated cost savings: ${estimated_savings:.4f}")
            summary.append(f" Latency improvement: {latency_benefit:.1f}%")
            
            # Show what was retrieved from cache
            if cache_info["turn"] == 1:
                summary.append(" Content retrieved from cache: Document context")
                cached_content = cache_info["cached_content"]
                if cached_content:
                    preview = cached_content[:100] + "..." if len(cached_content) > 100 else cached_content
                    summary.append(f" Cached content preview: \"{preview}\"")
            else:
                summary.append(" Content retrieved from cache: Previous question context")
                
            summary.append(" This means the model didn't need to process this content again,")
            summary.append(" resulting in faster response time and lower token usage.")
        else:
            summary.append(f" ❌ CACHE MISS")
            summary.append(f" Cache creation tokens: {input_tokens_cache_create}")
            
            # Show what was written to cache
            if cache_info["turn"] == 1:
                summary.append(" Content written to cache: Document context")
                cached_content = cache_info["cached_content"]
                if cached_content:
                    preview = cached_content[:100] + "..." if len(cached_content) > 100 else cached_content
                    summary.append(f" Cached content preview: \"{preview}\"")
            else:
                summary.append(" Content written to cache: Current question context")
                
            summary.append(" This content will be cached for future similar queries.")
            summary.append(" Future queries will benefit from faster response times and lower costs.")
            
        return "\n".join(summary)

class BedrockChat:
    """Main class for interacting with Bedrock for document Q&A
    
    This class orchestrates the document processing, model selection,
    and Bedrock API interactions with prompt caching capabilities.
    """
    
    def __init__(self):
        """Initialize the chat components and service dependencies"""
        # Initialize service components
        self.bedrock_service = BedrockService() # Manages Bedrock API clients
        self.runtime_client = self.bedrock_service.get_runtime_client() # For inference calls
        self.model_manager = ModelManager() # For model selection
        self.cache_manager = CacheManager() # For response caching
        
        # State variables
        self.current_document = "" # Currently loaded document
        self.current_model_id = "" # Selected model ID
        self.temperature = 0.0 # Temperature setting for generation
        self.blog = "" # For storing blog content for benchmarking
        
        # Get available models
        try:
            self.available_models = self.model_manager.get_available_models()
        except Exception as e:
            print(f"Warning: Could not fetch available models: {e}")
            self.available_models = [
                "anthropic.claude-haiku-4-5-20251001-v1:0",
                "anthropic.claude-sonnet-4-5-20250929-v1:0",
                "anthropic.claude-opus-4-1-20250805-v1:0"
            ]
    
    def set_document(self, document: str) -> None:
        """Set the current document for chat"""
        self.current_document = document
    
    def set_model(self, model_id: str) -> None:
        """Set the current model ID"""
        self.current_model_id = model_id
    
    def set_temperature(self, temperature: float) -> None:
        """Set the temperature for generation"""
        self.temperature = temperature
        
    def select_model(self):
        """Display available models and let user select one"""
        return self.model_manager.select_model()
    
    def chat_with_document(self, query: str, use_cache: bool = True, checkpoint: bool = False) -> Tuple[str, Dict, bool, str]:
        """
        Process a query against the current document
        
        Args:
            query: The user's question
            use_cache: Whether to check cache before calling Bedrock
            checkpoint: Whether to use a checkpoint for caching
            
        Returns:
            Tuple of (response_text, usage_info, from_cache, cache_key)
        """
        if not self.current_document:
            return "No document loaded. Please load a document first.", {}, False, ""
        
        if not self.current_model_id:
            return "No model selected. Please select a model first.", {}, False, ""
        
        # Check for empty query
        if not query.strip():
            return "Please enter a question.", {}, False, ""
        
        # Generate a simple cache key
        cache_key = f"{hash(self.current_document)}-{hash(query)}-{self.current_model_id}-{self.temperature}"
        
        # Prepare the prompt
        instructions = self._get_instructions()
        document_content = f"Here is the document: <document> {self.current_document} </document>"
        
        # Create message body based on cache settings
        if use_cache:
            # Include cache point for caching
            messages_body = [
                {
                    'role': 'user',
                    'content': [
                        {'text': instructions},
                        {'text': document_content},
                        {
                            "cachePoint": {
                                "type": "default"
                            }
                        },
                        {'text': query}
                    ]
                }
            ]
        else:
            # No cache point when caching is disabled
            messages_body = [
                {
                    'role': 'user',
                    'content': [
                        {'text': instructions},
                        {'text': document_content},
                        {'text': query}
                    ]
                }
            ]
        
        inference_config = {
            'maxTokens': 500,
            'temperature': self.temperature,
            'topP': 1
        }
        
        # Get updated model ID for specific Claude models
        model_id = self.model_manager.get_model_arn_from_inference_profiles(self.current_model_id)
        if model_id != self.current_model_id:
            print(f"\nUsing updated model ID: {model_id}")
        
        # Call Bedrock
        start_time = time.time()
        response = self.runtime_client.converse(
            messages=messages_body,
            modelId=model_id,
            inferenceConfig=inference_config
        )
        end_time = time.time()
        
        # Process response
        output_message = response["output"]["message"]
        response_text = output_message["content"][0]["text"]
        usage_info = response["usage"]
        
        # Add response time to usage info
        usage_info["response_time_seconds"] = end_time - start_time
        
        # Determine if this was a cache hit or miss based on metrics
        is_cache_hit = usage_info.get("cache_read_input_tokens", 0) > 0 or usage_info.get("cacheReadInputTokens", 0) > 0
        
        # Store cache information
        self.cache_manager.store_cache_info(
            cache_key=cache_key,
            is_cache_hit=is_cache_hit,
            document=self.current_document,
            query=query,
            metrics=usage_info
        )
        
        return response_text, usage_info, is_cache_hit, cache_key
    
    def _get_instructions(self) -> str:
        """Return the instructions for the LLM"""
        return (
            "I will provide you with a document, followed by a question about its content. "
            "Your task is to analyze the document, extract relevant information, and provide "
            "a comprehensive answer to the question. Please follow these detailed instructions:"

            "\n\n1. Identifying Relevant Quotes:"
            "\n - Carefully read through the entire document."
            "\n - Identify sections of the text that are directly relevant to answering the question."
            "\n - Select quotes that provide key information, context, or support for the answer."
            "\n - Quotes should be concise and to the point, typically no more than 2-3 sentences each."
            "\n - Choose a diverse range of quotes if multiple aspects of the question need to be addressed."
            "\n - Aim to select between 2 to 5 quotes, depending on the complexity of the question."

            "\n\n2. Presenting the Quotes:"
            "\n - List the selected quotes under the heading 'Relevant quotes:'"
            "\n - Number each quote sequentially, starting from [1]."
            "\n - Present each quote exactly as it appears in the original text, enclosed in quotation marks."
            "\n - If no relevant quotes can be found, write 'No relevant quotes' instead."

            "\n\n3. Formulating the Answer:"
            "\n - Begin your answer with the heading 'Answer:' on a new line after the quotes."
            "\n - Provide a clear, concise, and accurate answer to the question based on the information in the document."
            "\n - Ensure your answer is comprehensive and addresses all aspects of the question."
            "\n - Use information from the quotes to support your answer."
            "\n - Add the bracketed number of the relevant quote at the end of each sentence or point that uses information from that quote."

            "\n\n4. Handling Uncertainty:"
            "\n - If the document does not contain enough information to fully answer the question, clearly state this in your answer."
            "\n - Provide any partial information that is available."

            "\n\n5. Formatting and Style:"
            "\n - Use clear paragraph breaks to separate different points or aspects of your answer."
            "\n - Ensure proper grammar, punctuation, and spelling throughout your response."
            "\n - Maintain a professional and neutral tone throughout your answer."
        )
        
    def run_response_latency_benchmark(self, test_configs, epochs=3):
        """
        Benchmark response latency metrics for different models and cache modes
        
        Args:
            test_configs: List of test configuration dictionaries with model_id, model_name, and cache_mode
            epochs: Number of test iterations to run for each configuration
            
        Returns:
            List of datapoints with benchmark results
        """
        datapoints = []
        
        for test_config in test_configs: 
            print(f"[{test_config['model_name']}]")
            
            # Get updated model ID for specific Claude models
            model_id = self.model_manager.get_model_arn_from_inference_profiles(test_config['model_id'])
            if model_id != test_config['model_id']:
                print(f"Using updated model ID: {model_id}")
            
            # Prepare the converse command
            converse_cmd = {
                "modelId": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": []
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 500,
                    "temperature": self.temperature,
                    "topP": 1
                }
            }
                
            for cache_mode in test_config['cache_mode']:
                # Create a copy for modification
                cmd = converse_cmd.copy()
                
                # Set content with blog text
                cmd["messages"][0]["content"] = [
                    {
                        "text": self.blog
                    },
                    {
                        "text": "what is it about in 20 words."
                    }
                ]
                
                # Add cache point if needed
                if cache_mode == CACHE.ON:
                    cmd["messages"][0]["content"].insert(1, {
                        "cachePoint": {
                            "type": "default"
                        }
                    })
                
                for epoch in range(epochs):
                    start_time = time.time()
                    
                    # Call the API with streaming
                    response = self.runtime_client.converse_stream(**cmd)
                    
                    ttft = None
                    
                    for i, chunk in enumerate(response['stream']): 
                        if "messageStart" in chunk:
                            pass
                        elif "contentBlockStop" in chunk:
                            pass
                        elif "messageStop" in chunk:
                            pass
                        elif "contentBlockDelta" in chunk:
                            text = chunk["contentBlockDelta"].get('delta',{}).get("text",None) 
                            if text is not None and not text:
                                print('<empty>', end='')
                            if text is not None:
                                if not ttft:
                                    ttft = time.time() - start_time
                        
                        elif "metadata" in chunk: 
                            if 'cacheReadInputTokens' in chunk["metadata"]['usage']:
                                if chunk["metadata"]['usage']['cacheWriteInputTokens'] > 1:
                                    cache_result = CACHE.WRITE
                                elif chunk["metadata"]['usage']['cacheReadInputTokens'] > 1:
                                    cache_result = CACHE.READ
                                else:
                                    print(json.dumps(chunk, sort_keys=False, indent=4))
                                    assert False, 'Unclear'
                            else:
                                cache_result = CACHE.OFF
                                                    
                            latencyMs = chunk["metadata"]["metrics"]["latencyMs"] / 1000
                            requestId = response['ResponseMetadata']['RequestId']
                            
                            datapoints.append({ 
                                'model': test_config['model_name'],
                                'cache': cache_result,
                                'measure': 'first_token',
                                'time': ttft,
                                'requestId': requestId,
                            })
                            
                            datapoints.append({ 
                                'model': test_config['model_name'],
                                'cache': cache_result,
                                'measure': 'last_token',
                                'time': latencyMs,
                                'requestId': requestId,
                            })
                            
                            print(f"{epoch:2} {cache_mode},{cache_result} | ttft={ttft:.1f}s | last={latencyMs:.1f}s | {requestId}")
                        
                        else:
                            end_time = time.time()
                            print('\n\nchunk +{:.3f}s \n{}'.format(
                                time.time()-end_time,
                                json.dumps(chunk, sort_keys=False, indent=4)
                            ))
                    
                    time.sleep(30)
        
        return datapoints
        
    def add_median_labels(self, ax, fmt=".1f"):
        """
        Add text labels to the median lines of a seaborn boxplot.
        
        Args:
            ax: plt.Axes, e.g. the return value of sns.boxplot()
            fmt: format string for the median value
        """
        lines = ax.get_lines()
        boxes = [c for c in ax.get_children() if "Patch" in str(c)]
        start = 4
        if not boxes: # seaborn v0.13 => fill=False => no patches => +1 line
            boxes = [c for c in ax.get_lines() if len(c.get_xdata()) == 5]
            start += 1
        lines_per_box = len(lines) // len(boxes)
        for median in lines[start::lines_per_box]:
            x, y = (data.mean() for data in median.get_data())
            # choose value depending on horizontal or vertical plot orientation
            value = x if len(set(median.get_xdata())) == 1 else y
            text = ax.text(x, y, f'{value:{fmt}}', ha='center', va='center', color='white')
            # create median-colored border around white text for contrast
            text.set_path_effects([
                path_effects.Stroke(linewidth=3, foreground=median.get_color()),
                path_effects.Normal(),
            ])
            
    def visualize_benchmark(self, datapoints):
        """
        Visualize benchmark results using seaborn boxplots
        
        Args:
            datapoints: List of benchmark datapoints
        """
        if not datapoints:
            print("No benchmark data to visualize.")
            return
            
        df = pd.DataFrame(datapoints)
        
        # Save results to CSV for later analysis
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"benchmark_results_{timestamp}.csv"
            df.to_csv(csv_filename)
            print(f"Benchmark results saved to {csv_filename}")
        except Exception as e:
            print(f"Could not save results to CSV: {str(e)}")
        
        try:
            sns.set_style("whitegrid")
            n_models = df['model'].nunique()
            
            f, axes = plt.subplots(n_models, 1, figsize=(6, n_models * 6.4))
            
            # Convert axes to array if there's only one model
            axes = np.array([axes]) if n_models == 1 else axes
            
            for i, model in enumerate(df['model'].unique()):
                cond = df['model'] == model
                df_i = df.loc[cond]
                
                ax = sns.boxplot(df_i,
                             ax=axes[i],
                             x='measure', 
                             y='time', 
                             hue=df_i[['cache']].apply(tuple, axis=1)) 
            
                ax.tick_params(axis='x', rotation=45)
                ax.set_xlabel(None)
                self.add_median_labels(ax)
                ax.legend(loc='upper left')
                ax.set_title(f'Time to First Token (TTFT) - {model}', fontsize=14)
            
            plt.tight_layout()
            
            # Save plot to file
            try:
                plot_filename = f"benchmark_plot_{timestamp}.png"
                plt.savefig(plot_filename)
                print(f"Plot saved to {plot_filename}")
            except Exception as e:
                print(f"Could not save plot: {str(e)}")
                
            plt.show(block=False) # Non-blocking display
            plt.pause(0.1) # Small pause to render the plot
            
            input("\nPress Enter to continue...")
            plt.close()
        except Exception as e:
            print(f"Error during visualization: {str(e)}")

class ChatCLI:
    """Command-line interface for the Bedrock Chat application
    
    This class provides a user-friendly CLI for interacting with the BedrockChat
    functionality, including document loading, model selection, and chat sessions.
    """
    
    def __init__(self):
        """Initialize the CLI interface with sample content"""
        # Core chat functionality
        self.chat = BedrockChat()
        
        # Sample AWS blog URLs for demonstration
        self.sample_topics = [
            'https://aws.amazon.com/blogs/aws/reduce-costs-and-latency-with-amazon-bedrock-intelligent-prompt-routing-and-prompt-caching-preview/',
            'https://aws.amazon.com/blogs/machine-learning/enhance-conversational-ai-with-advanced-routing-techniques-with-amazon-bedrock/',
            'https://aws.amazon.com/blogs/security/cost-considerations-and-common-options-for-aws-network-firewall-log-management/'
        ]
        
        # Sample questions for user convenience
        self.sample_questions = [
            'what is it about?',
            'what are the use cases?',
            'Translate "Hello" to French (temperature=0.3)',
            'Translate "Hello" to French (temperature=0.4)'
        ]
        
    def _run_benchmark(self):
        """Run TTFT benchmark tests"""
        if not self.chat.current_document:
            print("\nNo document loaded. Please load a document first.")
            return
            
        if not self.chat.current_model_id:
            print("\nNo model selected. Please select a model first.")
            return
            
        # Store the current document as blog for benchmarking
        self.chat.blog = self.chat.current_document
        
        # Define test configurations
        tests = [
            {
                'model_id': self.chat.current_model_id,
                'model_name': self.chat.current_model_id.split(':')[0],
                'cache_mode': [CACHE.OFF, CACHE.ON]
            }
        ]
        
        # Ask for number of epochs
        try:
            epochs = int(input("\nEnter number of test iterations (default: 3): ") or "3")
        except ValueError:
            epochs = 3
            
        print(f"\nRunning benchmark with {epochs} iterations...")
        print("This may take several minutes. Please wait...")
        
        try:
            # Run the benchmark
            datapoints = self.chat.run_response_latency_benchmark(tests, epochs)
            
            # Visualize results
            print("\nGenerating visualization...")
            self.chat.visualize_benchmark(datapoints)
            
            # Show summary statistics
            df = pd.DataFrame(datapoints)
            print("\nBenchmark Results Summary:")
            print(df.groupby(['model', 'cache', 'measure'])['time'].agg(['mean', 'median', 'min', 'max']))
        except Exception as e:
            print(f"\nError during benchmark: {str(e)}")
            print("Returning to chat menu...")
    
    def display_welcome(self):
        """Display welcome message and system info"""
        print("\n" + "="*60)
        print("BEDROCK PROMPT CACHING CLI".center(60))
        print("="*60)
        print("\nSystem Information:")
        print(f"Bedrock Runtime Client initialized")
        print("\nThis application demonstrates Amazon Bedrock's prompt caching capabilities.")
        print("You can chat with documents and see if responses come from cache or LLM.")
        print("You can also use the multi-turn chat feature to visualize cache hits and misses.")
        print("="*60)
    
    def display_system_diagram(self):
        """Display a simple ASCII diagram of the system flow"""
        diagram = """
                System Flow Diagram: 
        ┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
        │ User Query  │────▶│ Cache Manager │────▶│ Cache Hit?      │
        └─────────────┘     └───────────────┘     └────────┬────────┘
               │                                           │
               │                                           │
               │                                      ┌────▼─────┐
        ┌──────▼──────┐     ┌───────────────┐        │          │
        │ Document    │     │ Bedrock       │   No   │   Yes    │
        │ Processor   │────▶│ Service       │◀───────┘          │
        └─────────────┘     └───────┬───────┘                   │
                                    │                           │
                                    │                           │
        ┌─────────────┐     ┌──────▼──────┐              ┌─────▼─────┐
        │ User        │◀────│ Response    │◀─────────────│ Retrieve  │
        │ Interface   │     │ Processing  │              │ from Cache│
        └─────────────┘     └────────────┘              └───────────┘
        """
        print(diagram)
    
    def load_document_menu(self):
        """Menu for loading a document"""
        print("\n--- DOCUMENT LOADING OPTIONS ---")
        print("1. Load from sample URLs")
        print("2. Enter custom URL")
        print("3. Enter file path")
        print("0. Return to main menu")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            print("\nSample URLs:")
            for i, url in enumerate(self.sample_topics, 1):
                print(f"{i}. {url}")
            
            url_choice = input("\nSelect URL number: ")
            try:
                url_index = int(url_choice) - 1
                if 0 <= url_index < len(self.sample_topics):
                    url = self.sample_topics[url_index]
                    print(f"\nFetching document from: {url}")
                    try:
                        response = requests.get(url)
                        response.raise_for_status()
                        document = response.text
                        if document:
                            self.chat.set_document(document)
                            print(f"Document loaded successfully ({len(document)} characters)")
                    except Exception as e:
                        print(f"Error fetching document: {e}")
                else:
                    print("Invalid selection")
            except ValueError:
                print("Please enter a valid number")
                
        elif choice == "2":
            url = input("\nEnter URL: ")
            print(f"Fetching document from: {url}")
            try:
                response = requests.get(url)
                response.raise_for_status()
                document = response.text
                if document:
                    self.chat.set_document(document)
                    print(f"Document loaded successfully ({len(document)} characters)")
            except Exception as e:
                print(f"Error fetching document: {e}")
                
        elif choice == "3":
            file_path = input("\nEnter file path: ")
            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() in FileProcessor.SUPPORTED_EXTENSIONS:
                try:
                    # Create a file-like object with name attribute for FileProcessor
                    import io
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    class FileObj:
                        def __init__(self, content, name):
                            self.name = name
                            self._content = content
                            self._io = io.BytesIO(content)
                        
                        def getvalue(self):
                            return self._content
                        
                        def seek(self, pos, whence=0):
                            return self._io.seek(pos, whence)
                        
                        def tell(self):
                            return self._io.tell()
                        
                        def read(self, size=-1):
                            return self._io.read(size)
                        
                        def close(self):
                            pass
                    
                    # Process the file using FileProcessor
                    file_obj = FileObj(file_content, os.path.basename(file_path))
                    document = FileProcessor.process_uploaded_file(file_obj)
                    file_obj.close()
                    
                    if document:
                        self.chat.set_document(document)
                        print(f"Document loaded successfully ({len(document)} characters)")
                        print("\nProceeding to model selection...")
                        self.model_selection_menu()
                except Exception as e:
                    print(f"Error processing file: {e}")
            else:
                print(f"Unsupported file type. Supported types: {', '.join(FileProcessor.SUPPORTED_EXTENSIONS)}")
    
    def model_selection_menu(self):
        """Menu for selecting a model"""
        model_id = self.chat.select_model()
        self.chat.set_model(model_id)
        print(f"\nSelected model: {model_id}")
        
        # Set temperature
        while True:
            try:
                temp = float(input("\nEnter temperature (0.0-1.0): "))
                if 0 <= temp <= 1:
                    self.chat.set_temperature(temp)
                    print(f"Temperature set to: {temp}")
                    break
                else:
                    print("Temperature must be between 0.0 and 1.0")
            except ValueError:
                print("Please enter a valid number")
    
    def chat_menu(self):
        """Interactive chat session with the document"""
        if not self.chat.current_document:
            print("\nNo document loaded. Please load a document first.")
            return
            
        if not self.chat.current_model_id:
            print("\nNo model selected. Please select a model first.")
            return
            
        print("\n--- CHAT SESSION ---")
        print("Type 'exit' to return to main menu")
        print("Type 'sample' to see sample questions")
        print("Type 'cache on/off' to toggle cache usage")
        print("Type 'benchmark' to run TTFT benchmarks")
        print("Type 'stats' to show cache statistics")
        
        use_cache = True
        last_cache_key = ""
        
        while True:
            print("\nSettings:")
            print(f"- Cache: {'ON' if use_cache else 'OFF'}")
            
            query = input("\nYour question: ")
            
            if query.lower() == 'exit':
                break
                
            elif query.lower() == 'sample':
                print("\nSample questions:")
                for i, q in enumerate(self.sample_questions, 1):
                    print(f"{i}. {q}")
                continue
                
            elif query.lower() == 'cache on':
                use_cache = True
                print("Cache enabled")
                continue
                
            elif query.lower() == 'cache off':
                use_cache = False
                print("Cache disabled")
                continue
                
            elif query.lower() == 'benchmark':
                self._run_benchmark()
                continue
                
            elif query.lower() == 'stats':
                if last_cache_key:
                    cache_summary = self.chat.cache_manager.get_cache_summary(last_cache_key)
                    print(cache_summary)
                else:
                    print("\nNo cache information available yet. Ask a question first.")
                continue
            
            # Process the query
            try:
                print("\nProcessing your question...")
                response_text, usage, from_cache, cache_key = self.chat.chat_with_document(
                    query, use_cache=use_cache
                )
                last_cache_key = cache_key
            except Exception as e:
                print(f"\nError: {str(e)}")
                continue
            
            # Display source information
            if from_cache:
                print("\n[RESPONSE FROM CACHE]")
            else:
                print("\n[RESPONSE FROM LLM]")
                
            # Display the response
            print("\n" + "="*60)
            print(response_text)
            print("="*60)
            
            # Display usage information
            print("\nUsage Information:")
            print(f"Input tokens: {usage.get('inputTokens', 'N/A')}")
            print(f"Output tokens: {usage.get('outputTokens', 'N/A')}")
            print(f"Response time: {usage.get('response_time_seconds', 'N/A'):.2f} seconds")
            
            # Display cache information
            cache_read = usage.get("cache_read_input_tokens", 0) or usage.get("cacheReadInputTokens", 0)
            cache_write = usage.get("cache_creation_input_tokens", 0) or usage.get("cacheCreationInputTokens", 0)
            
            # For cache hits from file cache, simulate cache metrics
            if from_cache and cache_read == 0:
                cache_read = usage.get("inputTokens", 0)
                
            if cache_read > 0:
                print(f"Cache read tokens: {cache_read}")
                print("✅ CACHE HIT: Content was retrieved from cache")
            elif cache_write > 0:
                print(f"Cache write tokens: {cache_write}")
                print("📝 CACHE WRITE: Content was written to cache")
            
            print("\nType 'stats' to see detailed cache information")
    
    def main_menu(self):
        """Main menu for the application"""
        self.display_welcome()
        self.display_system_diagram()
        
        while True:
            print("\n" + "="*60)
            print("MAIN MENU".center(60))
            print("="*60)
            print("1. Load Document")
            print("2. Select Model")
            print("3. Start Chat Session")
            print("0. Exit")
            
            choice = input("\nEnter your choice: ")
            
            if choice == "1":
                self.load_document_menu()
            elif choice == "2":
                self.model_selection_menu()
            elif choice == "3":
                self.chat_menu()
            elif choice == "0":
                print("\nExiting application. Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

def main():
    """Main entry point for the application
    
    Initializes the CLI interface and starts the main menu loop.
    """
    try:
        cli = ChatCLI()  # Create CLI instance
        cli.main_menu()  # Start the main menu
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        print("The application will now exit.")

if __name__ == "__main__":
    main()

