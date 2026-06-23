"""
Bedrock Prompt Caching Gradio Application

This module provides a web interface for the Bedrock Prompt Caching CLI application
using Gradio.
"""

import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import io
import time
import os
from PIL import Image
from typing import List, Tuple
import requests

# Import from the CLI module
from bedrock_prompt_caching import (
    BedrockChat, ModelManager, CACHE, BedrockService
)
from prompt_caching_multi_turn import PromptCachingExperiment
from file_processor import FileProcessor
from bedrock_claude_code import ClaudeSetup


class GradioBedrockApp:
    """Gradio interface for Bedrock Prompt Caching"""
    
    def __init__(self):
        """Initialize the Gradio application with required components"""
        # Initialize core components
        self.bedrock_service = BedrockService()
        self.chat = BedrockChat()
        self.model_manager = ModelManager()
        self.prompt_caching_experiment = PromptCachingExperiment(
            bedrock_service=self.bedrock_service,
            model_manager=self.model_manager
        )
        self.claude_setup = ClaudeSetup()
        
        # Sample URLs for demonstration
        self.sample_urls = [
            'https://aws.amazon.com/blogs/aws/reduce-costs-and-latency-with-amazon-bedrock-intelligent-prompt-routing-and-prompt-caching-preview/',
            'https://aws.amazon.com/blogs/machine-learning/enhance-conversational-ai-with-advanced-routing-techniques-with-amazon-bedrock/',
            'https://aws.amazon.com/blogs/security/cost-considerations-and-common-options-for-aws-network-firewall-log-management/'
        ]
        
        # Chat state management
        self.history = []  # Will store messages in dict format with 'role' and 'content' keys
        self.use_cache = True
        self.use_checkpoint = False
        
        # Multi-turn chat state
        self.multi_turn_conversation = []
        self.multi_turn_turn = 0
        self.multi_turn_context = ""
        
        # Common questions about Bedrock prompt caching for quick access
        self.common_questions = [
            "What is Amazon Bedrock prompt caching?",
            "How does prompt caching reduce costs?",
            "What are the benefits of using checkpoints?",
            "Which models support prompt caching?",
            "How much latency improvement can I expect?",
            "How is prompt caching different from RAG?",
            "Can I use prompt caching with streaming responses?",
            "How do I implement prompt caching in my application?",
            "What are the limitations of prompt caching?",
            "How does prompt caching handle similar but not identical prompts?"
        ]
        
        # Claude Code settings
        self.claude_working_dir = os.getcwd()
        self.claude_model = "sonnet"  # Default model
        self.claude_caching = True    # Default caching enabled
        
    def get_models(self) -> List[str]:
        """Get a flattened list of available models with caching support"""
        # Get models from the prompt_caching_experiment which has the latest model list
        # with proper caching support information
        all_models = []
        
        # Get models from model categories
        for category, models in self.model_manager.models.items():
            # Add category prefix to each model for better organization in dropdown
            for model in models:
                # Get the short name for display
                model_short = model.split('/')[-1].split(':')[0]
                all_models.append(f"{category}: {model_short}")
        
        return all_models
        
    def get_model_id_from_display_name(self, display_name: str) -> str:
        """Convert display name back to model ID"""
        if not display_name or ":" not in display_name:
            # Default to Claude 3.7 Sonnet if invalid
            return "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            
        # Extract category and model short name
        category, model_short = display_name.split(":", 1)
        model_short = model_short.strip()
        
        # Find matching model in the category
        if category in self.model_manager.models:
            for model_id in self.model_manager.models[category]:
                if model_short in model_id:
                    return model_id
        
        # If not found, use model_manager to resolve
        return self.model_manager.get_model_arn_from_inference_profiles(model_short)
    
    def load_document_from_url(self, url: str) -> str:
        """Load document from URL and set it as the current document"""
        if not url:
            return "Please enter a URL"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            document = response.text
            if document:
                self.chat.set_document(document)
                return f"Document loaded successfully ({len(document)} characters)"
            else:
                return "Empty document received from URL"
        except Exception as e:
            return f"Error fetching document from URL: {str(e)}"
    
    def load_document_from_file(self, file) -> str:
        """Load document from uploaded file and set it as the current document"""
        if file is None:
            return "No file uploaded"
        
        try:
            # Check if file is supported
            file_name = file.name if hasattr(file, 'name') else str(file)
            if not FileProcessor.is_supported_file(file_name):
                # Try to add the file extension to supported extensions
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext:
                    FileProcessor.SUPPORTED_EXTENSIONS.add(file_ext)
            
            # Handle file path case (when file is a path string)
            if isinstance(file, str) or (hasattr(file, 'name') and not hasattr(file, 'getvalue')):
                # If it's a file path, read the file directly
                try:
                    with open(file if isinstance(file, str) else file.name, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception as e:
                    return f"Error reading file: {str(e)}"
            else:
                # Process file using FileProcessor
                text = FileProcessor.process_uploaded_file(file)
                
            if text:
                self.chat.set_document(text)
                return f"Document loaded successfully ({len(text)} characters)"
            else:
                return "No text extracted from file"
        except Exception as e:
            return f"Error loading document: {str(e)}"
    
    def set_model_and_temp(self, display_name: str, temperature: float) -> str:
        """Set the model and temperature for inference"""
        # Convert display name to actual model ID
        model_id = self.get_model_id_from_display_name(display_name)
        
        # Resolve the model ID using model_manager if needed
        resolved_model_id = self.model_manager.get_model_arn_from_inference_profiles(model_id)
        if resolved_model_id != model_id:
            model_id = resolved_model_id
            
        self.chat.set_model(model_id)
        self.chat.set_temperature(temperature)
        
        # Return a more informative message
        model_short = model_id.split('/')[-1].split(':')[0]
        return f"Model set to {model_short} with temperature {temperature}"
    
    def toggle_cache(self, use_cache: bool) -> str:
        """Toggle cache usage on/off"""
        self.use_cache = use_cache
        return f"Cache {'enabled' if use_cache else 'disabled'}"
    
    def toggle_checkpoint(self, use_checkpoint: bool) -> str:
        """Toggle checkpoint usage on/off"""
        self.use_checkpoint = use_checkpoint
        return f"Checkpoint {'enabled' if use_checkpoint else 'disabled'}"
    
    def chat_with_document(self, query: str) -> Tuple[List, str, str, str]:
        """Process a query against the loaded document and update chat history"""
        if not self.chat.current_document:
            return self.history, "No document loaded. Please load a document first.", "", ""
        
        if not self.chat.current_model_id:
            return self.history, "No model selected. Please select a model first.", "", ""
        
        if not query.strip():
            return self.history, "Please enter a question.", "", ""
        
        try:
            # Measure response time
            start_time = time.time()
            response_text, usage, from_cache, cache_key = self.chat.chat_with_document(
                query, use_cache=self.use_cache, checkpoint=False
            )
            cache_retrieval_time = time.time() - start_time
            
            # Format usage info based on cache hit or miss
            cache_read = usage.get("cache_read_input_tokens", 0) or usage.get("cacheReadInputTokens", 0)
            cache_write = usage.get("cache_creation_input_tokens", 0) or usage.get("cacheCreationInputTokens", 0)
            
            # For cache hits from file cache, simulate cache metrics
            if from_cache and cache_read == 0:
                cache_read = usage.get("inputTokens", 0)
                
            if from_cache:
                # Calculate latency benefit percentage
                standard_response_time = 2.0  # Estimated standard response time without cache
                latency_benefit = ((standard_response_time - cache_retrieval_time) / standard_response_time) * 100
                
                # Calculate token savings
                token_savings_percentage = (cache_read / (cache_read + usage.get("inputTokens", 0))) * 100 if cache_read > 0 else 0
                
                usage_info = (
                    f"Response retrieved from cache\n"
                    f"Cache retrieval time: {cache_retrieval_time:.4f} seconds\n"
                    f"Cache hit: {self.use_cache}\n"
                    f"Cache read tokens: {cache_read}\n"
                    f"Latency reduction: {latency_benefit:.1f}%\n"
                    f"Token savings: {token_savings_percentage:.1f}%"
                )
            else:
                usage_info = (
                    f"Input tokens: {usage.get('inputTokens', 'N/A')}\n"
                    f"Output tokens: {usage.get('outputTokens', 'N/A')}\n"
                    f"Response time: {usage.get('response_time_seconds', 'N/A'):.2f} seconds"
                )
                
                if cache_write > 0:
                    usage_info += f"\nCache write tokens: {cache_write}"
            
            # Get detailed cache summary
            cache_summary = ""
            if cache_key:
                cache_summary = self.chat.cache_manager.get_cache_summary(cache_key)
                
                # Add cache checkpoint information
                input_tokens = usage.get('inputTokens', 0)
                cache_read_tokens = usage.get('cache_read_input_tokens', 0) or usage.get('cacheReadInputTokens', 0)
                total_tokens = input_tokens + cache_read_tokens  # Total tokens including those from cache
                model_name = self.chat.current_model_id
                
                # Determine minimum token requirements based on model
                min_tokens = 1024  # Default minimum for most models
                if "claude-3-7-sonnet" in model_name:
                    min_tokens = 1024
                elif "claude-3-5" in model_name:
                    min_tokens = 1024
                elif "nova" in model_name:
                    min_tokens = 512
                
                # Add cache checkpoint information
                cache_summary += "\n\n### Cache Checkpoint Information\n"
                cache_summary += "Cache checkpoints have minimum token requirements that vary by model:\n"
                cache_summary += f"- Current model: {model_name}\n"
                cache_summary += f"- Minimum tokens required: {min_tokens}\n"
                cache_summary += f"- Your total tokens: {total_tokens} (input: {input_tokens}, cache: {cache_read_tokens})\n"
                
                # Determine if document meets minimum requirements based on total tokens
                if total_tokens >= min_tokens:
                    cache_summary += f"✅ Your prompt meets the minimum token requirement ({total_tokens} ≥ {min_tokens})\n"
                    cache_summary += f"- First checkpoint can be defined after {min_tokens} tokens\n"
                    cache_summary += f"- Second checkpoint can be defined after {min_tokens * 2} tokens\n"
                else:
                    cache_summary += f"❌ Your prompt does not meet the minimum token requirement ({total_tokens} < {min_tokens})\n"
                    cache_summary += "- Your prefix will not be cached\n"
                
                cache_summary += "\nCache has a five minute Time To Live (TTL), which resets with each successful cache hit."
                cache_summary += "\nIf no cache hits occur within the TTL window, your cache expires."
                
                # Add business benefits section to cache summary
                if from_cache:
                    cache_summary += "\n\n### Business Benefits of Prompt Caching\n"
                    cache_summary += "- **Cost Reduction**: Cached tokens pricing is different from LLM token usage costs\n"
                    cache_summary += "- **Improved Latency**: Faster responses by skipping redundant processing\n"
                    cache_summary += "- **Consistent Responses**: Same prompts yield identical outputs\n"
                    cache_summary += "- **Scalability**: Handle more requests with the same resources\n"
            
            # Update history with the new Q&A pair using messages format
            self.history.append({"role": "user", "content": query})
            self.history.append({"role": "assistant", "content": response_text})
            
            return self.history, "", usage_info, cache_summary
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            # Special handling for specific models that might cause issues
            if "claude-3-5-sonnet" in self.chat.current_model_id or "nova-pro" in self.chat.current_model_id:
                error_message = f"This model ({self.chat.current_model_id}) currently has compatibility issues with prompt caching. Please try a different model."
            
            # Return all four expected values even in case of error
            return self.history, error_message, "", ""
    
    def clear_history(self) -> Tuple[List, str, str, str]:
        """Clear the chat history"""
        self.history = []
        return [], "Chat history cleared", "No queries yet", "No cache information yet"
    
    def run_benchmark(self, epochs: int) -> Tuple[str, str]:
        """Run TTFT (Time To First Token) benchmark tests"""
        if not self.chat.current_document:
            return "No document loaded. Please load a document first.", None
            
        if not self.chat.current_model_id:
            return "No model selected. Please select a model first.", None
            
        print(f"Running benchmark with {epochs} iterations...")
        print("This may take several minutes. Please wait...")
        
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
        
        try:
            # Run the benchmark
            datapoints = self.chat.run_response_latency_benchmark(tests, epochs)
            
            # Create visualization
            if not datapoints:
                return "No benchmark data to visualize.", None
                
            df = pd.DataFrame(datapoints)
            
            # Save results to CSV for later analysis
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            csv_filename = f"benchmark_results_{timestamp}.csv"
            df.to_csv(csv_filename)
            
            # Create plot
            plt_img = self._create_benchmark_plot(df)
            
            # Print raw data for debugging
            print("Raw benchmark data:")
            for dp in datapoints:
                print(f"{dp['model']} - {dp['cache']} - {dp['measure']} - {dp['time']:.2f}s")
                
            # Format summary statistics in a more readable way
            summary = df.groupby(['model', 'cache', 'measure'])['time'].agg(['mean', 'median', 'min', 'max'])
            
            # Create a more readable summary text
            summary_text = "## Benchmark Results Summary\n\n"
            
            # Process each model separately
            for model_name in summary.index.get_level_values('model').unique():
                model_short_name = model_name.split('-')[0].split('.')[-1].capitalize()
                summary_text += f"### Model: {model_short_name}\n\n"
                
                # Get cache modes for this model
                cache_modes = summary.loc[model_name].index.get_level_values('cache').unique()
                
                # Store baseline values for comparison
                baseline_first_token = None
                baseline_last_token = None
                
                # Get baseline values from CACHE.OFF if available
                if "CACHE.OFF" in cache_modes:
                    try:
                        baseline_first_token = summary.loc[(model_name, "CACHE.OFF", 'first_token')]
                        baseline_last_token = summary.loc[(model_name, "CACHE.OFF", 'last_token')]
                    except:
                        pass
                
                for cache_mode in cache_modes:
                    # Map the cache mode to a user-friendly status
                    if cache_mode == "CACHE.OFF":
                        cache_status = "Cache OFF"
                    elif cache_mode == "CACHE.ON":
                        cache_status = "Cache ON"
                    elif cache_mode == "CACHE.READ":
                        cache_status = "Cache HIT"
                    elif cache_mode == "CACHE.WRITE":
                        cache_status = "Cache WRITE"
                    else:
                        cache_status = str(cache_mode)
                        
                    summary_text += f"#### {cache_status}\n\n"
                    
                    # Format as a table with wider columns to accommodate percentages
                    summary_text += "| Metric | Mean (sec) | Median (sec) | Min (sec) | Max (sec) |\n"
                    summary_text += "|--------|-------------------|-------------------|----------------|----------------|\n"
                    
                    try:
                        # First token metrics
                        first_token = summary.loc[(model_name, cache_mode, 'first_token')]
                        
                        # Calculate percentage differences for all metrics
                        mean_diff = median_diff = min_diff = max_diff = ""
                        
                        if cache_mode != "CACHE.OFF" and baseline_first_token is not None:
                            # For mean
                            if baseline_first_token['mean'] > 0:
                                mean_pct = ((baseline_first_token['mean'] - first_token['mean']) / baseline_first_token['mean']) * 100
                                mean_diff = f" ({mean_pct:.1f}% {'faster' if mean_pct > 0 else 'slower'})"
                            
                            # For median
                            if baseline_first_token['median'] > 0:
                                median_pct = ((baseline_first_token['median'] - first_token['median']) / baseline_first_token['median']) * 100
                                median_diff = f" ({median_pct:.1f}% {'faster' if median_pct > 0 else 'slower'})"
                            
                            # For min
                            if baseline_first_token['min'] > 0:
                                min_pct = ((baseline_first_token['min'] - first_token['min']) / baseline_first_token['min']) * 100
                                min_diff = f" ({min_pct:.1f}% {'faster' if min_pct > 0 else 'slower'})"
                            
                            # For max
                            if baseline_first_token['max'] > 0:
                                max_pct = ((baseline_first_token['max'] - first_token['max']) / baseline_first_token['max']) * 100
                                max_diff = f" ({max_pct:.1f}% {'faster' if max_pct > 0 else 'slower'})"
                                
                        summary_text += f"| Time to First Token | {first_token['mean']:.2f}{mean_diff} | {first_token['median']:.2f}{median_diff} | {first_token['min']:.2f}{min_diff} | {first_token['max']:.2f}{max_diff} |\n"
                        
                        # Last token metrics
                        last_token = summary.loc[(model_name, cache_mode, 'last_token')]
                        
                        # Calculate percentage differences for all metrics
                        mean_diff = median_diff = min_diff = max_diff = ""
                        
                        if cache_mode != "CACHE.OFF" and baseline_last_token is not None:
                            # For mean
                            if baseline_last_token['mean'] > 0:
                                mean_pct = ((baseline_last_token['mean'] - last_token['mean']) / baseline_last_token['mean']) * 100
                                mean_diff = f" ({mean_pct:.1f}% {'faster' if mean_pct > 0 else 'slower'})"
                            
                            # For median
                            if baseline_last_token['median'] > 0:
                                median_pct = ((baseline_last_token['median'] - last_token['median']) / baseline_last_token['median']) * 100
                                median_diff = f" ({median_pct:.1f}% {'faster' if median_pct > 0 else 'slower'})"
                            
                            # For min
                            if baseline_last_token['min'] > 0:
                                min_pct = ((baseline_last_token['min'] - last_token['min']) / baseline_last_token['min']) * 100
                                min_diff = f" ({min_pct:.1f}% {'faster' if min_pct > 0 else 'slower'})"
                            
                            # For max
                            if baseline_last_token['max'] > 0:
                                max_pct = ((baseline_last_token['max'] - last_token['max']) / baseline_last_token['max']) * 100
                                max_diff = f" ({max_pct:.1f}% {'faster' if max_pct > 0 else 'slower'})"
                                
                        summary_text += f"| Total Response Time | {last_token['mean']:.2f}{mean_diff} | {last_token['median']:.2f}{median_diff} | {last_token['min']:.2f}{min_diff} | {last_token['max']:.2f}{max_diff} |\n"
                    except:
                        summary_text += "| Data not available | - | - | - | - |\n"
                    
                    summary_text += "\n"
                
                # Calculate speedup if we have both cache off and any cache on mode
                try:
                    # Find all first token times for each cache mode
                    cache_times = {}
                    for mode in cache_modes:
                        try:
                            cache_times[mode] = summary.loc[(model_name, mode, 'first_token')]['mean']
                        except:
                            pass
                    
                    # If we have both OFF and any other mode, calculate speedup
                    if 'CACHE.OFF' in cache_times:
                        cache_off_time = cache_times['CACHE.OFF']
                        
                        # Find the best cache hit time (READ is preferred)
                        cache_hit_time = None
                        hit_mode = None
                        for mode in ['CACHE.READ', 'CACHE.ON', 'CACHE.WRITE']:
                            if mode in cache_times:
                                cache_hit_time = cache_times[mode]
                                hit_mode = mode
                                break
                        
                        if cache_hit_time is not None and cache_off_time > 0 and hit_mode is not None:
                            speedup = (cache_off_time - cache_hit_time) / cache_off_time * 100
                            
                            # Calculate token savings if available
                            token_savings = "N/A"
                            try:
                                # Get average token usage for each mode
                                cache_read_tokens = 0
                                
                                # Try different column names for cache read tokens
                                for col_name in ['cacheReadInputTokens', 'cache_read_input_tokens']:
                                    if col_name in df.columns:
                                        cache_read_tokens = df[df['cache'] == hit_mode][col_name].mean()
                                        if not pd.isna(cache_read_tokens) and cache_read_tokens > 0:
                                            break
                                
                                # Get input tokens
                                input_tokens = 0
                                for col_name in ['inputTokens', 'input_tokens']:
                                    if col_name in df.columns:
                                        input_tokens = df[df['cache'] == 'CACHE.OFF'][col_name].mean()
                                        if not pd.isna(input_tokens) and input_tokens > 0:
                                            break
                                
                                if input_tokens > 0 and cache_read_tokens > 0:
                                    token_savings = (cache_read_tokens / input_tokens) * 100
                            except Exception as e:
                                print(f"Error calculating token savings: {e}")
                                
                            summary_text += f"**Cache Speedup: {speedup:.1f}%** (comparing CACHE.OFF vs {hit_mode})\n\n"
                            if token_savings != "N/A":
                                summary_text += f"**Token Savings: {token_savings:.1f}%** of input tokens retrieved from cache\n\n"
                            
                            # Add business impact
                            summary_text += "### Business Benefits\n\n"
                            summary_text += "- **Cost Reduction**: Lower token usage means reduced API costs\n"
                            summary_text += "- **Improved User Experience**: Faster response times lead to better user engagement\n"
                            summary_text += "- **Higher Throughput**: Process more requests with the same resources\n"
                            summary_text += "- **Reduced Latency**: Critical for real-time applications\n\n"
                except Exception as e:
                    print(f"Error calculating speedup: {e}")
            
            summary_text += f"\nResults saved to {csv_filename}"
            
            return summary_text, plt_img
            
        except Exception as e:
            return f"Error during benchmark: {str(e)}", None
    
    def _create_benchmark_plot(self, df):
        """Create benchmark plot comparing cache performance and return as image"""
        import seaborn as sns
        import numpy as np
        
        plt.figure(figsize=(10, 8))
        sns.set_style("whitegrid")
        n_models = df['model'].nunique()
        
        f, axes = plt.subplots(n_models, 1, figsize=(10, n_models * 6))
        
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
            self._add_median_labels(ax)
            ax.legend(loc='upper left')
            ax.set_title(f'Time to First Token (TTFT) - {model}', fontsize=14)
        
        plt.tight_layout()
        
        # Convert plot to image
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt_img = Image.open(buf)
        
        return plt_img
    
    def _add_median_labels(self, ax, fmt=".1f"):
        """Add text labels to the median lines of a seaborn boxplot"""
        lines = ax.get_lines()
        boxes = [c for c in ax.get_children() if "Patch" in str(c)]
        start = 4
        if not boxes:  # seaborn v0.13 => fill=False => no patches => +1 line
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
    
    # Multi-Turn Chat Methods
    def load_multi_turn_document_from_url(self, url: str) -> str:
        """Load document from URL for multi-turn chat"""
        if not url:
            return "Please enter a URL"
        
        try:
            result = self.prompt_caching_experiment.load_context_from_url(url)
            if result:
                self.multi_turn_context = self.prompt_caching_experiment.sample_text
                self.multi_turn_conversation = []
                self.multi_turn_turn = 0
                return f"Document loaded successfully ({len(self.multi_turn_context)} characters)"
            else:
                return "Failed to load document from URL"
        except Exception as e:
            return f"Error loading document from URL: {str(e)}"
    
    def load_multi_turn_document_from_file(self, file) -> str:
        """Load document from file for multi-turn chat"""
        if file is None:
            return "No file uploaded"
        
        try:
            # Handle file path case (when file is a path string)
            if isinstance(file, str) or (hasattr(file, 'name') and not hasattr(file, 'getvalue')):
                # If it's a file path, read the file directly
                file_path = file if isinstance(file, str) else file.name
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    # Set the content directly
                    self.multi_turn_context = file_content
                    self.multi_turn_conversation = []
                    self.multi_turn_turn = 0
                    self.prompt_caching_experiment.set_context_text(file_content)
                    return f"Document loaded successfully ({len(file_content)} characters)"
                except Exception as e:
                    return f"Error reading file: {str(e)}"
            else:
                # Get file path from Gradio file object
                file_path = file.name if hasattr(file, 'name') else file
                
                result = self.prompt_caching_experiment.load_context_from_file(file_path)
                if result:
                    self.multi_turn_context = self.prompt_caching_experiment.sample_text
                    self.multi_turn_conversation = []
                    self.multi_turn_turn = 0
                    return f"Document loaded successfully ({len(self.multi_turn_context)} characters)"
                else:
                    return "Failed to load document from file"
        except Exception as e:
            return f"Error loading document: {str(e)}"
    
    def set_multi_turn_model(self, display_name: str) -> str:
        """Set the model for multi-turn chat"""
        # Convert display name to actual model ID
        model_id = self.get_model_id_from_display_name(display_name)
        
        # Resolve the model ID using model_manager
        resolved_model_id = self.model_manager.get_model_arn_from_inference_profiles(model_id)
        if resolved_model_id != model_id:
            model_id = resolved_model_id
            
        self.multi_turn_model_id = model_id
        
        # Get a shorter display name for the model
        model_short = model_id.split('/')[-1].split(':')[0]
        return f"Using model: {model_short}"
    
    def multi_turn_chat(self, query: str, max_tokens: int = 2048, temperature: float = 0.5, 
                       top_p: float = 0.8, top_k: int = 250, stop_sequences: str = "") -> Tuple[List, str, str]:
        """Process a query in multi-turn chat mode with model parameters"""
        if not self.multi_turn_context:
            return [], "No document loaded. Please load a document first.", ""
        
        if not hasattr(self, 'multi_turn_model_id'):
            # Default model
            default_model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            self.multi_turn_model_id = self.model_manager.get_model_arn_from_inference_profiles(default_model)
        
        if not query.strip():
            return [], "Please enter a question.", ""
        
        try:
            # Set the context text in the experiment
            self.prompt_caching_experiment.set_context_text(self.multi_turn_context)
            
            # Record the start time
            start_time = time.time()
            
            # Convert stop_sequences from string to list if provided
            stop_seq_list = None
            if stop_sequences:
                stop_seq_list = [seq.strip() for seq in stop_sequences.split(',')]
            
            # Store model parameters in experiment
            self.prompt_caching_experiment.model_params = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": 250,  # Add top_k for Anthropic models
                "stop_sequences": stop_seq_list
            }
            
            # Process the turn with model parameters
            turn_data = self.prompt_caching_experiment.process_turn(
                self.multi_turn_turn,
                self.multi_turn_conversation,
                query,
                self.multi_turn_model_id
            )
            
            # Add the turn data to the experiment's all_experiments_data
            self.prompt_caching_experiment.all_experiments_data.append(turn_data)
            
            # Record the end time
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Increment turn counter
            self.multi_turn_turn += 1
            
            # Get the response text
            if self.multi_turn_conversation and len(self.multi_turn_conversation) >= 2:
                response_text = self.multi_turn_conversation[-1]["content"][0]["text"]
            else:
                response_text = "No response generated."
            
            # Format chat history for display with messages format
            chat_history = []
            for i, msg in enumerate(self.multi_turn_conversation):
                if msg["role"] == "user":
                    # Skip displaying the context text for readability
                    if i == 0 and len(msg["content"]) > 1:
                        user_text = msg['content'][-1]['text']
                    else:
                        user_text = ' '.join([c['text'] for c in msg['content'] if 'text' in c])
                    chat_history.append({"role": "user", "content": user_text})
                else:
                    chat_history.append({"role": "assistant", "content": msg['content'][0]['text']})
            
            # Get turn metrics using the prompt_caching_experiment's method
            turn_metrics = self.prompt_caching_experiment.get_turn_metrics(turn_data)
            
            # Get cache summary using the prompt_caching_experiment's method
            cache_summary = self.prompt_caching_experiment.get_cache_summary(turn_data)
            
            # Combine metrics and cache summary for display
            usage_info = f"{turn_metrics}\n\n{cache_summary}"
            
            # Add business benefits if this is a cache hit
            if turn_data['is_cache_hit']:
                # Calculate latency benefit percentage
                standard_response_time = 2.0  # Estimated standard response time without cache
                latency_benefit = ((standard_response_time - elapsed_time) / standard_response_time) * 100
                
                # Calculate token savings
                input_tokens = turn_data['input_tokens']
                input_tokens_cache_read = turn_data['cache_read_input_tokens']
                token_savings_percentage = (input_tokens_cache_read / (input_tokens_cache_read + input_tokens) * 100) if input_tokens_cache_read > 0 else 0
                
                # Add business benefits section
                usage_info += "\n\n### Business Benefits of Prompt Caching\n"
                usage_info += f"- **Cost Reduction**: {token_savings_percentage:.1f}% token savings\n"
                usage_info += f"- **Improved Latency**: {latency_benefit:.1f}% faster response time\n"
                usage_info += "- **Consistent Responses**: Same prompts yield identical outputs\n"
                usage_info += "- **Scalability**: Handle more requests with the same resources\n"
            
            return chat_history, "", usage_info
            
        except Exception as e:
            return [], f"Error: {str(e)}", ""
    
    def clear_multi_turn_history(self) -> Tuple[List, str]:
        """Clear the multi-turn chat history"""
        self.multi_turn_conversation = []
        self.multi_turn_turn = 0
        return [], "Chat history cleared"
        
    def show_experiment_stats(self) -> str:
        """Show summary statistics for the multi-turn chat experiment"""
        # Access the experiment data directly from the experiment object
        all_experiments_data = self.prompt_caching_experiment.all_experiments_data
        
        if not all_experiments_data:
            return "No experiment data available. Please chat with the model first."
        
        try:
            # Use the experiment's built-in method to get a formatted summary
            return self.prompt_caching_experiment.get_experiment_summary()
            
        except Exception as e:
            return f"Error generating statistics: {str(e)}"
            
    # Claude Code methods
    
    def get_current_working_dir(self) -> str:
        """Get the current working directory for Claude Code"""
        return self.claude_working_dir
    
    def change_working_dir(self, new_dir: str) -> str:
        """Change the working directory for Claude Code"""
        try:
            if not os.path.exists(new_dir):
                return f"Directory does not exist: {new_dir}"
            
            if not os.path.isdir(new_dir):
                return f"Not a directory: {new_dir}"
                
            self.claude_working_dir = new_dir
            return f"Working directory changed to: {new_dir}"
        except Exception as e:
            return f"Error changing directory: {str(e)}"
    
    def install_claude_code(self) -> str:
        """Install Claude Code using npm"""
        try:
            # Show progress message
            yield "Installing Claude Code... This may take a moment."
            
            import subprocess
            result = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"], 
                                   capture_output=True, text=True)
            if result.returncode != 0:
                yield f"Error installing Claude Code: {result.stderr}"
            else:
                yield "Claude Code installed successfully."
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def check_aws_config(self) -> str:
        """Check AWS configuration"""
        try:
            import subprocess
            result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                return f"AWS credentials configured correctly:\n{result.stdout}"
            else:
                return f"AWS credentials not configured correctly:\n{result.stderr}"
        except Exception as e:
            return f"Error checking AWS configuration: {str(e)}"
    
    def check_claude_version(self) -> str:
        """Check Claude Code version"""
        try:
            import subprocess
            result = subprocess.run(["claude", "--version"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                return f"Claude Code version: {result.stdout}"
            else:
                return f"Error checking Claude Code version: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def configure_claude_environment(self, model: str, enable_caching: bool) -> str:
        """Configure environment variables for Claude Code"""
        try:
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
            
            if model == "haiku":
                model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
                os.environ["ANTHROPIC_MODEL"] = model_id
                os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = model_id
                model_name = "Claude 3.5 Haiku"
                self.claude_model = "haiku"
            else:
                model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
                os.environ["ANTHROPIC_MODEL"] = model_id
                model_name = "Claude 3.7 Sonnet"
                self.claude_model = "sonnet"
            
            if enable_caching:
                if "DISABLE_PROMPT_CACHING" in os.environ:
                    del os.environ["DISABLE_PROMPT_CACHING"]
                caching_status = "enabled"
                self.claude_caching = True
            else:
                os.environ["DISABLE_PROMPT_CACHING"] = "true"
                caching_status = "disabled"
                self.claude_caching = False
                
            return f"Environment configured with {model_name} ({model_id}). Prompt caching is {caching_status}."
        except Exception as e:
            return f"Error configuring environment: {str(e)}"
    
    def generate_environment_script(self, model: str, enable_caching: bool) -> str:
        """Generate a script with environment variables for Claude Code"""
        try:
            if model == "haiku":
                model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
                model_name = "Claude 3.5 Haiku"
            else:
                model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
                model_name = "Claude 3.7 Sonnet"
            
            script = f"""#!/bin/bash
# Environment setup for {model_name}

# Set Bedrock integration
export CLAUDE_CODE_USE_BEDROCK=1

# Set model
export ANTHROPIC_MODEL='{model_id}'
"""
            
            if model == "haiku":
                script += f"export ANTHROPIC_SMALL_FAST_MODEL='{model_id}'\n"
                
            if enable_caching:
                script += """
# Enable prompt caching
# Remove DISABLE_PROMPT_CACHING if it exists
if [ -n "$DISABLE_PROMPT_CACHING" ]; then
    unset DISABLE_PROMPT_CACHING
fi
"""
            else:
                script += """
# Disable prompt caching
export DISABLE_PROMPT_CACHING=true
"""
                
            script += """
# Launch Claude Code
claude
"""
            return script
        except Exception as e:
            return f"# Error generating script: {str(e)}"
    
    def run_claude_setup_script(self) -> str:
        """Run the bedrock_claude_code.py setup script"""
        try:
            yield "Running Claude Code setup script..."
            
            # Get the script path
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bedrock_claude_code.py")
            
            # Check if the script exists
            if not os.path.exists(script_path):
                return f"Error: Setup script not found at {script_path}"
            
            # Run the script
            import subprocess
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Read output in real-time
            while True:
                # Check if process has terminated
                if process.poll() is not None:
                    # Read any remaining output
                    remaining_stdout, remaining_stderr = process.communicate()
                    if remaining_stdout:
                        yield f"Script output: {remaining_stdout}"
                    if remaining_stderr:
                        yield f"Script errors: {remaining_stderr}"
                    break
                
                # Read available output without blocking
                stdout_chunk = process.stdout.readline()
                if stdout_chunk:
                    yield f"Script output: {stdout_chunk}"
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.1)
            
            yield "Claude Code setup script completed. Please check your terminal for the interactive Claude Code session."
        except Exception as e:
            yield f"Error running Claude Code setup script: {str(e)}"
    
    def launch_claude_shell(self) -> str:
        """Launch Claude Code shell directly"""
        try:
            yield "Launching Claude Code shell..."
            
            # Configure environment variables
            env_vars = os.environ.copy()
            env_vars["CLAUDE_CODE_USE_BEDROCK"] = "1"
            
            # Use the model from dropdown
            if hasattr(self, 'claude_model') and self.claude_model == "haiku":
                env_vars["ANTHROPIC_MODEL"] = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
                env_vars["ANTHROPIC_SMALL_FAST_MODEL"] = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
            else:
                env_vars["ANTHROPIC_MODEL"] = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            
            # Handle caching setting
            if hasattr(self, 'claude_caching') and self.claude_caching:
                if "DISABLE_PROMPT_CACHING" in env_vars:
                    del env_vars["DISABLE_PROMPT_CACHING"]
            else:
                env_vars["DISABLE_PROMPT_CACHING"] = "true"
            
            # Launch Claude shell
            import subprocess
            subprocess.run(["claude"], env=env_vars, cwd=self.claude_working_dir)
            
            yield "Claude Code shell session ended."
        except Exception as e:
            yield f"Error launching Claude Code shell: {str(e)}"
    



def create_gradio_interface():
    """Create and launch the Gradio interface"""
    app = GradioBedrockApp()
    
    with gr.Blocks(title="Amazon Bedrock Prompt Caching Demo") as interface:
        gr.Markdown("# Amazon Bedrock Prompt Caching Demo")
        gr.Image("/Users/arunmamb/myTechs/bedrock/bedrock-prompt-caching/src/images/prompt-caching.png", label="Prompt Caching Diagram")
        
        with gr.Tabs() as tabs:
            # RAG Chat Tab
            with gr.TabItem("RAG Chat"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 1. Load Document")
                        
                        with gr.Tab("From URL"):
                            url_input = gr.Textbox(label="Enter URL")
                            url_examples = gr.Examples(
                                examples=app.sample_urls,
                                inputs=url_input
                            )
                            load_url_btn = gr.Button("Load from URL")
                            url_status = gr.Textbox(label="Status", interactive=False)
                        
                        with gr.Tab("From File"):
                            file_input = gr.File(label="Upload Document")
                            load_file_btn = gr.Button("Load File")
                            file_status = gr.Textbox(label="Status", interactive=False)
                        
                        gr.Markdown("### 2. Select Model")
                        model_dropdown = gr.Dropdown(
                            choices=app.get_models(),
                            label="Model (with caching support)",
                            value=app.get_models()[0] if app.get_models() else None,
                            info="Select a model that supports prompt caching"
                        )
                        temperature_slider = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.1,
                            label="Temperature"
                        )
                        set_model_btn = gr.Button("Set Model")
                        model_status = gr.Textbox(label="Status", interactive=False)
                        
                        gr.Markdown("### Settings")
                        cache_checkbox = gr.Checkbox(label="Use Cache", value=True)
                        gr.Markdown("""
                        #### Cache Checkpoint Information
                        Cache checkpoints have minimum token requirements:
                        - Claude 3.7 Sonnet: 1,024 tokens minimum
                        - Claude 3.5 models: 1,024 tokens minimum
                        - Nova models: 512 tokens minimum
                        
                        Cache has a 5-minute TTL that resets with each hit.
                        
                        #### Model Format Information
                        - Anthropic Claude models: Use "cache_control" with "ephemeral" type
                        - Amazon Nova models: Use "cachePoint" with "default" type
                        """)
                        
                        gr.Markdown("### Benchmark")
                        epochs_slider = gr.Slider(
                            minimum=1,
                            maximum=10,
                            value=3,
                            step=1,
                            label="Test Iterations"
                        )
                        benchmark_btn = gr.Button("Run Benchmark")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### Chat")
                        chatbot = gr.Chatbot(height=500, type="messages")
                        msg = gr.Textbox(label="Your Question")
                        
                        with gr.Row():
                            submit_btn = gr.Button("Submit")
                            clear_btn = gr.Button("Clear History")
                        
                        error_output = gr.Textbox(label="Error", visible=True, interactive=False)
                        usage_info = gr.Textbox(label="Usage Information", interactive=False)
                        cache_stats = gr.Textbox(label="Cache Statistics", interactive=False, lines=10)
                        
                        with gr.Accordion("Common Questions", open=False):
                            common_q_btns = [gr.Button(q) for q in app.common_questions]
                
                with gr.Accordion("Benchmark Results", open=False):
                    with gr.Row():
                        benchmark_output = gr.Markdown(label="Benchmark Results")
                        benchmark_plot = gr.Image(label="Benchmark Plot")
            
            # Multi-Turn Chat Tab
            with gr.TabItem("Multi-Turn Chat"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 1. Load Document")
                        
                        with gr.Tab("From URL"):
                            mt_url_input = gr.Textbox(label="Enter URL")
                            mt_url_examples = gr.Examples(
                                examples=app.sample_urls,
                                inputs=mt_url_input
                            )
                            mt_load_url_btn = gr.Button("Load from URL")
                            mt_url_status = gr.Textbox(label="Status", interactive=False)
                        
                        with gr.Tab("From File"):
                            mt_file_input = gr.File(label="Upload Document")
                            mt_load_file_btn = gr.Button("Load File")
                            mt_file_status = gr.Textbox(label="Status", interactive=False)
                        
                        gr.Markdown("### 2. Select Model")
                        mt_model_dropdown = gr.Dropdown(
                            choices=app.get_models(),
                            label="Model (with caching support)",
                            value=app.get_models()[0] if app.get_models() else None,
                            info="Select a model that supports prompt caching"
                        )
                        
                        gr.Markdown("### 3. Model Parameters")
                        with gr.Row():
                            mt_max_tokens = gr.Number(value=2048, label="Max Tokens", minimum=1, maximum=4096, step=1)
                            mt_temperature = gr.Slider(value=0.5, label="Temperature", minimum=0.0, maximum=1.0, step=0.1)
                        
                        with gr.Row():
                            mt_top_p = gr.Slider(value=0.8, label="Top P", minimum=0.0, maximum=1.0, step=0.1)
                            mt_top_k = gr.Number(value=250, label="Top K (Anthropic only)", minimum=0, maximum=500, step=1)
                        
                        mt_stop_sequences = gr.Textbox(value="", label="Stop Sequences (comma-separated)")
                        
                        mt_set_model_btn = gr.Button("Set Model")
                        mt_model_status = gr.Textbox(label="Status", interactive=False)
                        
                        gr.Markdown("### Experiment Results")
                        mt_show_stats_btn = gr.Button("Show Summary Statistics")
                        mt_stats_output = gr.Markdown(label="Summary Statistics")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### Multi-Turn Chat with Prompt Caching")
                        mt_chatbot = gr.Chatbot(height=500, type="messages")
                        mt_msg = gr.Textbox(label="Your Question")
                        
                        with gr.Row():
                            mt_submit_btn = gr.Button("Submit")
                            mt_clear_btn = gr.Button("Clear History")
                        
                        mt_error_output = gr.Textbox(label="Error", visible=True, interactive=False)
                        mt_usage_info = gr.Markdown(label="Cache & Performance Metrics")
            
            # Claude Code Tab
            with gr.TabItem("Claude Code"):
                with gr.Row():
                    # Left column for reference information
                    with gr.Column(scale=1):
                        gr.Markdown("## Claude Code Reference")
                        
                        with gr.Accordion("Command Line Setup", open=True):
                            gr.Markdown("""
                            ### Running Claude Code from the Command Line
                            
                            To use Claude Code, open a terminal and run:
                            
                            ```bash
                            # Navigate to the project directory
                            cd <project_root>
                            
                            # Run the Claude Code setup script
                            python3 src/bedrock_claude_code.py
                            ```
                            
                            This will guide you through setup and launch Claude Code.
                            """)
                        
                        # Keep hidden elements for backward compatibility
                        install_btn = gr.Button("Install Claude Code", visible=False)
                        install_status = gr.Textbox(label="Installation Status", interactive=False, visible=False)
                        check_aws_btn = gr.Button("Check AWS Configuration", visible=False)
                        aws_status = gr.Textbox(label="AWS Status", interactive=False, visible=False)
                        check_version_btn = gr.Button("Check Claude Version", visible=False)
                        version_status = gr.Textbox(label="Version Information", interactive=False, visible=False)
                        cc_model_dropdown = gr.Dropdown(
                            choices=[
                                {"label": "Claude 3.7 Sonnet", "value": "sonnet", "info": "us.anthropic.claude-3-7-sonnet-20250219-v1:0"},
                                {"label": "Claude 3.5 Haiku", "value": "haiku", "info": "us.anthropic.claude-3-5-haiku-20241022-v1:0"}
                            ],
                            label="Model",
                            value="sonnet",
                            info="Select Claude model to use",
                            visible=False
                        )
                        cc_cache_checkbox = gr.Checkbox(label="Enable Prompt Caching", value=True, visible=False)
                        configure_btn = gr.Button("Configure Environment", visible=False)
                        configure_status = gr.Textbox(label="Configuration Status", interactive=False, visible=False)
                        generate_script_btn = gr.Button("Generate Script", visible=False)
                        script_output = gr.Code(language="shell", label="Environment Script", lines=10, visible=False)
                    
                    # Right column for instructions
                    with gr.Column(scale=2):
                        gr.Markdown("# Getting Started with Claude Code: Step-by-Step Guide")
                        
                        with gr.Accordion("Getting Started with Claude Code", open=True):
                            gr.Markdown("""
                            ### Quick Start with bedrock_claude_code.py
                            
                            The easiest way to get started with Claude Code is to run the provided script:
                            
                            ```bash
                            # Navigate to the project root directory
                            cd <project_root>
                            
                            # Run the Claude Code setup script
                            python3 src/bedrock_claude_code.py
                            ```
                            
                            This script will:
                            1. Install Claude Code if needed
                            2. Let you select the Claude model (Sonnet or Haiku)
                            3. Configure prompt caching
                            4. Launch the Claude Code interactive shell
                            
                            ### What to Expect
                            
                            When you run the script, you'll see:
                            ```
                            === Claude Code Setup Chat ===
                            User: I need to set up Claude Code with Bedrock.
                            Assistant: I'll help you set up Claude Code with Bedrock. Running the setup now...
                            Installing Claude Code...
                            Claude Code installed successfully.
                            
                            A: Which Claude model would you like to use?
                            1. Claude 3.7 Sonnet (more capable)
                            2. Claude 3.5 Haiku (faster)
                            Enter your choice (1 or 2): 
                            ```
                            
                            After making your selections, Claude Code will launch automatically.
                            """)
                            
                        with gr.Accordion("Learning Claude Code Commands", open=False):
                            gr.Markdown("""
                            ### Initialize a Project
                            ```bash
                            # Inside your project directory
                            claude
                            > /init
                            ```
                            This scans your project and creates a CLAUDE.md guide

                            ### Get Help with Available Commands
                            ```bash
                            > /help
                            ```

                            ### Try Basic Coding Assistance
                            ```bash
                            > Create a simple HTML calculator
                            ```
                            Review Claude's suggestions. When prompted to create files, type "yes" to approve.

                            ### View Project Files
                            ```bash
                            > /ls
                            ```

                            ### Examine File Contents
                            ```bash
                            > /cat calculator.html
                            ```

                            ### Edit a File
                            ```bash
                            > Edit calculator.html to add scientific functions
                            ```

                            ### Run Commands in the Terminal
                            ```bash
                            > /sh ls -la
                            ```
                            """)
                            
                        with gr.Accordion("Managing Context and Costs", open=False):
                            gr.Markdown("""
                            ### Check Token Usage
                            ```bash
                            > /cost
                            ```

                            ### Compact the Conversation
                            ```bash
                            > /compact
                            ```
                            This preserves important context while reducing token usage

                            ### Clear the Conversation
                            ```bash
                            > /clear
                            ```
                            Use when starting a completely new task
                            """)
                            
                        with gr.Accordion("Advanced Usage", open=False):
                            gr.Markdown("""
                            ### Work with Multiple Files
                            ```bash
                            > Create a complete web app with HTML, CSS, and JavaScript files for a todo list
                            ```
                            Notice how Claude handles multiple file creation and relationships

                            ### Debug Code Issues
                            ```bash
                            > There's a bug in my calculator.html file where division by zero doesn't show an error. Can you fix it?
                            ```

                            ### Explain Code Architecture
                            ```bash
                            > Explain how the JavaScript functions in calculator.html work together
                            ```

                            ### Generate Tests
                            ```bash
                            > Create test cases for the calculator functions
                            ```

                            ### Optimize Code
                            ```bash
                            > Optimize the calculator.js file for better performance
                            ```
                            """)
                            
                        with gr.Accordion("Tips for Effective Usage", open=False):
                            gr.Markdown("""
                            - **Be Specific**: Provide clear, detailed instructions
                            - **Review Changes**: Always review code before approving file modifications
                            - **Use /compact Regularly**: Helps manage token usage during long sessions
                            - **Create Project Structure**: Start with a clear project outline for better results
                            - **Ask for Explanations**: If you don't understand Claude's suggestions, ask for clarification
                            - **Monitor Costs**: Use the /cost command periodically to track token usage
                            
                            This step-by-step guide will help you learn Claude Code effectively through hands-on practice with the command line interface. Each step builds on the previous one, allowing you to gradually explore more advanced features as you become comfortable with the basics.
                            """)
                        
                        # Hidden element for backward compatibility
                        current_dir = gr.Textbox(label="Current Directory", value=os.getcwd(), interactive=False, visible=False)
        
        # Single-Turn Chat Event handlers
        load_url_btn.click(
            fn=app.load_document_from_url,
            inputs=[url_input],
            outputs=[url_status]
        )
        
        load_file_btn.click(
            fn=app.load_document_from_file,
            inputs=[file_input],
            outputs=[file_status]
        )
        
        set_model_btn.click(
            fn=app.set_model_and_temp,
            inputs=[model_dropdown, temperature_slider],
            outputs=[model_status]
        )
        
        cache_checkbox.change(
            fn=app.toggle_cache,
            inputs=[cache_checkbox],
            outputs=[]
        )
        

        
        submit_btn.click(
            fn=app.chat_with_document,
            inputs=[msg],
            outputs=[chatbot, error_output, usage_info, cache_stats],
            api_name="chat"
        )
        
        clear_btn.click(
            fn=app.clear_history,
            inputs=[],
            outputs=[chatbot, error_output, usage_info, cache_stats]
        )
        
        benchmark_btn.click(
            fn=app.run_benchmark,
            inputs=[epochs_slider],
            outputs=[benchmark_output, benchmark_plot]
        )
        
        # Connect common question buttons
        for btn in common_q_btns:
            btn.click(
                fn=app.chat_with_document,
                inputs=[btn],
                outputs=[chatbot, error_output, usage_info, cache_stats]
            )
        
        # Multi-Turn Chat Event handlers
        mt_load_url_btn.click(
            fn=app.load_multi_turn_document_from_url,
            inputs=[mt_url_input],
            outputs=[mt_url_status]
        )
        
        mt_load_file_btn.click(
            fn=app.load_multi_turn_document_from_file,
            inputs=[mt_file_input],
            outputs=[mt_file_status]
        )
        
        mt_set_model_btn.click(
            fn=app.set_multi_turn_model,
            inputs=[mt_model_dropdown],
            outputs=[mt_model_status]
        )
        
        mt_submit_btn.click(
            fn=app.multi_turn_chat,
            inputs=[mt_msg, mt_max_tokens, mt_temperature, mt_top_p, mt_top_k, mt_stop_sequences],
            outputs=[mt_chatbot, mt_error_output, mt_usage_info],
            api_name="multi_turn_chat"
        ).then(
            fn=lambda: "",
            outputs=[mt_msg]
        )
        
        mt_clear_btn.click(
            fn=app.clear_multi_turn_history,
            inputs=[],
            outputs=[mt_chatbot, mt_error_output]
        )
        
        mt_show_stats_btn.click(
            fn=app.show_experiment_stats,
            inputs=[],
            outputs=[mt_stats_output]
        )
        
        # Claude Code Event handlers
        install_btn.click(
            fn=app.install_claude_code,
            inputs=[],
            outputs=[install_status]
        )
        
        configure_btn.click(
            fn=app.configure_claude_environment,
            inputs=[cc_model_dropdown, cc_cache_checkbox],
            outputs=[configure_status]
        )
        
        # Remove directory handlers
        
        # This handler is already defined above
        
        # No run script button handler needed
        
        # Keep handlers for backward compatibility (hidden elements)
        check_aws_btn.click(
            fn=app.check_aws_config,
            inputs=[],
            outputs=[aws_status]
        )
        
        check_version_btn.click(
            fn=app.check_claude_version,
            inputs=[],
            outputs=[version_status]
        )
        
        generate_script_btn.click(
            fn=app.generate_environment_script,
            inputs=[cc_model_dropdown, cc_cache_checkbox],
            outputs=[script_output]
        )
    
    return interface


if __name__ == "__main__":
    interface = create_gradio_interface()
    interface.launch(share=False)