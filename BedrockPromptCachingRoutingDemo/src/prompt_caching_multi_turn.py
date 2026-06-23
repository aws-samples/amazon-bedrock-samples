import time
import json
import os
import pandas as pd
import hashlib
import requests
from file_processor import FileProcessor
from bedrock_service import BedrockService
from model_manager import ModelManager


class PromptCachingExperiment:
    """Handles prompt caching experiments with foundation models
    
    This class provides functionality for running multi-turn conversations
    with prompt caching, collecting metrics, and analyzing cache performance.
    It can be used standalone or integrated with other applications.
    """
    
    def __init__(self, bedrock_service=None, model_manager=None):
        """Initialize the experiment with Bedrock service and model manager
        
        Args:
            bedrock_service: BedrockService instance for making API calls
                             If None, a new instance will be created
            model_manager: ModelManager instance for model selection and resolution
                          If None, a new instance will be created
                          
        Raises:
            TypeError: If provided services are not of the correct type
        """
        # Validate service types if provided
        if bedrock_service is not None and not isinstance(bedrock_service, BedrockService):
            raise TypeError("bedrock_service must be an instance of BedrockService")
            
        if model_manager is not None and not isinstance(model_manager, ModelManager):
            raise TypeError("model_manager must be an instance of ModelManager")
        
        # Use provided services or create new ones if not provided
        self.bedrock_service = bedrock_service if bedrock_service else BedrockService()
        self.model_manager = model_manager if model_manager else ModelManager(self.bedrock_service)
        
        self.all_experiments_data = []  # Stores metrics for all conversation turns
        self.cache_store = {}           # Stores cache information by cache key
        self.sample_text = ""           # Context text, set by set_context_text
        
        # Default model parameters
        self.model_params = {
            "max_tokens": 2048,
            "temperature": 0.5,
            "top_p": 0.8,
            "stop_sequences": None
        }
            
        # Default questions for each turn in automated experiments
        self.default_questions = [
            "Please summarize the story.",
            "What is the subject of the story?",
            "Where did Romeo and Juliet first meet?",
            "What is the name of the woman Romeo loved before?",
            "How does Mercutio die?",
            "What method did Juliet use to fake her death?",
        ]
    
    def set_context_text(self, text):
        """Set the context text for the experiment
        
        Args:
            text: The text to use as context
        """
        self.sample_text = text
        print(f"Context text set ({len(text)} characters)")
    
    def load_context_from_file(self, file_path):
        """Load context text from a file using FileProcessor
        
        Args:
            file_path: Path to the file to load
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if file extension is supported
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in FileProcessor.SUPPORTED_EXTENSIONS:
                print(f"Unsupported file type. Supported types: {', '.join(FileProcessor.SUPPORTED_EXTENSIONS)}")
                return False
                
            # Create a file-like object with name attribute for FileProcessor
            class FileObj:
                def __init__(self, path):
                    self.name = os.path.basename(path)
                    self._file = open(path, 'rb')
                
                def getvalue(self):
                    self._file.seek(0)
                    return self._file.read()
                
                def close(self):
                    self._file.close()
            
            # Process the file using FileProcessor
            file_obj = FileObj(file_path)
            self.sample_text = FileProcessor.process_uploaded_file(file_obj)
            file_obj.close()
            
            if not self.sample_text:
                print("No text extracted from file.")
                return False
                
            print(f"Context loaded from file: {file_path} ({len(self.sample_text)} characters)")
            return True
        except Exception as e:
            print(f"Error loading context from file: {e}")
            return False
    
    def load_context_from_url(self, url):
        """Load context text from a URL
        
        Args:
            url: URL to fetch the context from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            self.sample_text = response.text
            
            if not self.sample_text:
                print("Empty document received from URL.")
                return False
                
            print(f"Context loaded from URL: {url} ({len(self.sample_text)} characters)")
            return True
        except Exception as e:
            print(f"Error loading context from URL: {e}")
            return False
    
    def run_experiments(self, n_experiments=1, n_turns=6, model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0"):
        """Run multiple experiments with multi-turn conversations
        
        Args:
            n_experiments: Number of experiment iterations to run
            n_turns: Number of conversation turns in each experiment
            model_id: The Bedrock model ID to use (default: Claude 3.7 Sonnet)
            
        Returns:
            List of all turn data dictionaries from the experiments
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not self.sample_text:
            print("No context text set. Please set context text before running experiments.")
            return []
            
        if n_experiments < 1:
            raise ValueError("Number of experiments must be at least 1")
            
        if n_turns < 1:
            raise ValueError("Number of turns must be at least 1")
            
        if not model_id or not isinstance(model_id, str):
            raise ValueError("Model ID must be a non-empty string")
            
        print(f"Running experiments with model: {model_id}")
        print("Enabling cache testing mode - will repeat the same question twice to test caching")
        print("\nCache Information:")
        print("- First turn always includes context text which will be cached")
        
        all_experiment_data = []
        
        for exp_num in range(n_experiments):
            print(f"Running experiment {exp_num+1}/{n_experiments}")
            experiment_data = []
            conversation = []

            # Simulate n_turns
            for turn in range(n_turns):
                # Get the current question
                question = self.default_questions[min(turn, len(self.default_questions)-1)]
                
                # For even turns after turn 0, repeat the previous question to test caching
                if turn > 0 and turn % 2 == 0:
                    question = self.default_questions[min(turn-1, len(self.default_questions)-1)]
                    print(f"  Turn {turn+1}/{n_turns}: {question} (REPEATED to test cache)")
                else:
                    print(f"  Turn {turn+1}/{n_turns}: {question}")
                
                turn_data = self.process_turn(turn, conversation, question, model_id)
                experiment_data.append(turn_data)
                time.sleep(30)  # Wait between requests

            all_experiment_data.extend(experiment_data)
            self.all_experiments_data.extend(experiment_data)
            
        # Save results
        self.save_results()
        
        return all_experiment_data
    
    def interactive_chat(self, model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0"):
        """Run an interactive chat session where user can type questions
        
        Args:
            model_id: The Bedrock model ID to use (default: Claude 3.7 Sonnet)
            
        Returns:
            List of turn data dictionaries containing metrics for all turns
            
        Raises:
            ValueError: If model_id is invalid
        """
        if not self.sample_text:
            print("No context text set. Please set context text before starting chat.")
            return []
            
        if not model_id or not isinstance(model_id, str):
            raise ValueError("Model ID must be a non-empty string")
            
        print(f"Starting interactive chat session with context ({len(self.sample_text)} characters)")
        print(f"Using model: {model_id}")
        print("Type 'exit' to end the conversation")
        print("Type 'model:<model_id>' to change the model")
        print("Type 'select' to select a model from the list")
        print("Type 'stats' to show experiment statistics")
        print("\nCache Information:")
        print("- First turn always includes context text which will be cached")
        
        conversation = []
        turn_data = []
        turn = 0
        
        # First turn always includes the sample text
        while True:
            if turn == 0:
                print("\nFirst message will include the context text")
            
            # Get user question
            user_question = input("\nEnter your question: ")
            if user_question.lower() == 'exit':
                break
            
            # Check if user wants to change the model
            if user_question.lower().startswith('model:'):
                new_model_id = user_question[6:].strip()
                model_id = self.model_manager.get_model_arn_from_inference_profiles(new_model_id)
                print(f"Model changed to: {model_id}")
                continue
            
            # Check if user wants to select a model from the list
            if user_question.lower() == 'select':
                model_id = self.model_manager.select_model()
                print(f"Model selected: {model_id}")
                continue
                
            # Check if user wants to see experiment statistics
            if user_question.lower() == 'stats':
                if turn_data:
                    self.display_metrics()
                else:
                    print("No experiment data available yet.")
                continue
                
            # Process the turn
            data = self.process_turn(turn, conversation, user_question, model_id)
            turn_data.append(data)
            
            # Print the response
            print("\nAssistant:", conversation[-1]["content"][0]["text"])
            
            # Print metrics for this turn
            print("\n" + self.get_turn_metrics(data))
            
            # Print cache information
            self.print_cache_info(data)
            
            turn += 1
        
        # Save results if any turns were processed
        if turn_data:
            self.all_experiments_data.extend(turn_data)
            self.save_results()
            self.display_metrics()
    
    def process_turn(self, turn, conversation, question, model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0"):
        """Process a single conversation turn with prompt caching
        
        This method handles the core functionality of the experiment:
        - Constructing the message with appropriate cache controls
        - Invoking the model with the provided conversation history
        - Collecting and returning detailed metrics about the interaction
        - Updating the conversation history with the new turn
        
        Args:
            turn: The turn number (0-based) in the conversation
            conversation: The conversation history list that will be modified in-place
            question: The user question to process in this turn
            model_id: The Bedrock model ID to use (default: Claude 3.7 Sonnet)
            
        Returns:
            Dictionary containing detailed metrics for this turn including:
            - turn: Turn number (1-based)
            - question: The question that was asked
            - input_tokens: Number of input tokens processed
            - output_tokens: Number of output tokens generated
            - cache_creation_input_tokens: Number of tokens written to cache
            - cache_read_input_tokens: Number of tokens read from cache
            - invocation_latency: Total time taken for the request
            - cache_key: Unique key for this content in the cache
            - is_cache_hit: Boolean indicating if cache was hit
            
        Raises:
            ValueError: If parameters are invalid or sample_text is not set
            RuntimeError: If model invocation fails
        """
        if not isinstance(conversation, list):
            raise ValueError("Conversation must be a list")
            
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")
            
        if turn == 0 and not self.sample_text:
            raise ValueError("Context text not set. Call set_context_text before processing the first turn.")
            
        if not isinstance(turn, int) or turn < 0:
            raise ValueError("Turn must be a non-negative integer")
            
        # Get the resolved model ID from the model manager
        model_id = self.model_manager.get_model_arn_from_inference_profiles(model_id)
            
        # Generate a cache key for this content
        cache_key = self.generate_cache_key(self.sample_text if turn == 0 else "", question)
        
        # Determine if this is a Claude model or Nova model
        is_claude_model = "anthropic" in model_id.lower() or "claude" in model_id.lower()  # Used throughout the method
        
        # Construct message content for this turn based on model type
        content = []
        if turn == 0:
            if is_claude_model:
                content.append({"type": "text", "text": self.sample_text})
            else:
                # For Nova models, no "type" field
                content.append({"text": self.sample_text})
        
        # Add the current question - format depends on model type
        if is_claude_model:
            content.append({
                "type": "text",
                "text": question + " "
            })
        else:
            content.append({
                "text": question + " "
            })
        
        # Construct full messages list with history + current message
        messages = conversation.copy()
        messages.append({"role": "user", "content": content})
        
        # Prepare version without cache control for conversation history
        content_for_saving = []
        if turn == 0:
            if is_claude_model:
                content_for_saving.append({"type": "text", "text": self.sample_text})
            else:
                # For Nova models, no "type" field
                content_for_saving.append({"text": self.sample_text})
        
        # Add question with format based on model type
        if is_claude_model:
            content_for_saving.append({"type": "text", "text": question + " "})
        else:
            content_for_saving.append({"text": question + " "})

        # Print request info
        print("\n" + "="*60)
        print(f"🔄 PROCESSING TURN {turn+1}")
        print("="*60)
        print(f"Question: \"{question}\"")
        print(f"Cache key: {cache_key}")
        print(f"Model: {model_id}")
        
        # Check if this is a repeated question
        if cache_key in [data.get("cache_key") for data in self.all_experiments_data]:
            print("⚠️ This question was asked before - potential cache hit!")
        
        # Show what's being sent
        if turn == 0:
            print(f"📄 Including context text ({len(self.sample_text)} characters)")
            context_preview = self.sample_text[:100] + "..." if len(self.sample_text) > 100 else self.sample_text
            print(f"Context preview: \"{context_preview}\"")
        else:
            print("📝 Using conversation history from previous turns")
        
        # Record the start time for performance measurement
        start_time = time.time()
        
        try:
            response = self.invoke_model(messages, model_id, self.model_params)
        except Exception as e:
            raise RuntimeError(f"Model invocation failed: {str(e)}")
        
        # Record the end time
        end_time = time.time()
        invocation_latency = end_time - start_time
        
        # Validate response format
        if not isinstance(response, dict) or "content" not in response or "usage" not in response:
            raise RuntimeError("Invalid response format from model")
        
        # Ensure content has the expected structure
        if not response["content"] or not isinstance(response["content"], list):
            raise RuntimeError("Invalid content format in response")
            
        # Update conversation history - reuse the is_claude_model variable from earlier
        
        # Add user message to conversation history
        if is_claude_model:
            conversation.append({"role": "user", "content": content_for_saving})
        else:
            # For Nova models, no "type" field in content
            nova_content = []
            for item in content_for_saving:
                if "text" in item:
                    nova_content.append({"text": item["text"]})
            conversation.append({"role": "user", "content": nova_content})
        
        # Add assistant response to conversation history
        try:
            if is_claude_model:
                conversation.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": response["content"][0]["text"]}]
                })
            else:
                # For Nova models, no "type" field
                conversation.append({
                    "role": "assistant",
                    "content": [{"text": response["content"][0]["text"]}]
                })
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to extract response text: {str(e)}")

        # Get metrics - handle different field names for different models
        metrics = response["usage"]
        
        # Normalize metrics field names
        input_tokens = metrics.get("input_tokens", metrics.get("inputTokens", 0))
        output_tokens = metrics.get("output_tokens", metrics.get("outputTokens", 0))
        cache_read_tokens = metrics.get("cache_read_input_tokens", metrics.get("cacheReadInputTokens", 0))
        cache_write_tokens = metrics.get("cache_creation_input_tokens", metrics.get("cacheWriteInputTokens", 0))
        
        # Store cache information
        is_cache_hit = cache_read_tokens > 0
        cache_info = {
            "cache_key": cache_key,
            "is_cache_hit": is_cache_hit,
            "cached_content": self.sample_text if turn == 0 else "",
            "question": question,
            "cache_creation_tokens": cache_write_tokens,
            "cache_read_tokens": cache_read_tokens
        }
        self.cache_store[cache_key] = cache_info

        # Return data for this turn with normalized field names
        return {
            "turn": turn + 1,
            "question": question,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_write_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "invocation_latency": invocation_latency,
            "cache_key": cache_key,
            "is_cache_hit": is_cache_hit
        }
    
    def generate_cache_key(self, context, question):
        """Generate a simple cache key for tracking cached content
        
        Args:
            context: The context text (if any)
            question: The question text
            
        Returns:
            A hash string to use as cache key
        """
        content = (context + question).encode('utf-8')
        return hashlib.md5(content).hexdigest()[:8]
    
    def get_cache_summary(self, turn_data):
        """Get cache summary information as a formatted string
        
        This method analyzes the cache performance for a specific turn
        and generates a detailed summary of cache usage, including:
        - Cache hit/miss status
        - Token savings from cache
        - Percentage of prompt that was cached
        - Description of what content was cached or retrieved
        
        Args:
            turn_data: Dictionary containing the turn metrics from process_turn
            
        Returns:
            Formatted string with cache summary information ready for display
        """
        cache_key = turn_data["cache_key"]
        is_cache_hit = turn_data["is_cache_hit"]
        
        # Calculate performance metrics
        input_tokens = turn_data['input_tokens']
        input_tokens_cache_read = turn_data['cache_read_input_tokens']
        input_tokens_cache_create = turn_data['cache_creation_input_tokens']
        total_input_tokens = input_tokens + input_tokens_cache_read
        percentage_cached = (input_tokens_cache_read / total_input_tokens * 100) if total_input_tokens > 0 else 0
        
        summary = ["\n📊 Cache Summary:"]
        summary.append(f"  Cache key: {cache_key}")
        
        if is_cache_hit:
            summary.append(f"  ✅ CACHE HIT")
            summary.append(f"  Cache read tokens: {input_tokens_cache_read}")
            summary.append(f"  Input tokens saved: {input_tokens_cache_read}")
            summary.append(f"  {percentage_cached:.1f}% of input prompt cached ({total_input_tokens} tokens)")
            
            # Show what was retrieved from cache
            if turn_data["turn"] == 1:
                summary.append("  Content retrieved from cache: Context text (first turn)")
                cached_content = self.sample_text[:100] + "..." if len(self.sample_text) > 100 else self.sample_text
                summary.append(f"  Cached content preview: \"{cached_content}\"")
            else:
                summary.append("  Content retrieved from cache: Previous question context")
                
            summary.append("  This means the model didn't need to process this content again,")
            summary.append("  resulting in faster response time and lower token usage.")
        else:
            summary.append(f"  ❌ CACHE MISS")
            summary.append(f"  Cache creation tokens: {input_tokens_cache_create}")
            
            # Show what was written to cache
            if turn_data["turn"] == 1:
                summary.append("  Content written to cache: Context text (first turn)")
                cached_content = self.sample_text[:100] + "..." if len(self.sample_text) > 100 else self.sample_text
                summary.append(f"  Cached content preview: \"{cached_content}\"")
            else:
                summary.append("  Content written to cache: Current question context")
                
            summary.append("  This content will be cached for future similar queries.")
            
        return "\n".join(summary)
    
    def print_cache_info(self, turn_data):
        """Print information about cache usage for this turn
        
        Args:
            turn_data: Data for the current turn
        """
        summary = self.get_cache_summary(turn_data)
        print(summary)
    
    def invoke_model(self, messages, model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0", model_params=None):
        """Invoke foundation model through Bedrock with appropriate caching strategy
        
        This method handles the different invocation patterns required for different models:
        - Anthropic Claude models: Uses invoke_model API with cache_control
        - Amazon Nova models: Uses converse API with cachePoint
        
        Args:
            messages: The conversation messages to send (list of message objects)
            model_id: The Bedrock model ID to use (default: Claude 3.7 Sonnet)
            
        Returns:
            Standardized response dictionary with:
            - content: List of content blocks with text
            - usage: Dictionary with token usage metrics
            
        Raises:
            ValueError: If bedrock_service is not initialized or messages is invalid
            boto3.exceptions.Boto3Error: For AWS service-related errors
        """
        if not self.bedrock_service:
            raise ValueError("BedrockService not initialized. Please provide a valid bedrock_service in the constructor.")
        
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list")
            
        try:
            runtime_client = self.bedrock_service.get_runtime_client()
        except Exception as e:
            raise ValueError(f"Failed to get Bedrock runtime client: {str(e)}")
        
        # Get the resolved model ID from the model manager
        resolved_model_id = self.model_manager.get_model_arn_from_inference_profiles(model_id)
        if resolved_model_id != model_id:
            print(f"Using resolved model ID: {resolved_model_id}")
            model_id = resolved_model_id
        
        # For Anthropic Claude models
        if "anthropic" in model_id.lower() or "claude" in model_id.lower():
            # Use the invoke_model API with the proper format for Claude models
            # Prepare user message with cache control
            user_message = None
            for msg in messages:
                if msg["role"] == "user":
                    user_message = msg
                    break
            
            if user_message and len(user_message["content"]) > 1:
                # Format the content with cache_control for the second part
                content_with_cache = []
                for i, content_item in enumerate(user_message["content"]):
                    if i == 0:  # First item (context)
                        content_with_cache.append(content_item)
                    else:  # Second item (question)
                        content_with_cache.append({
                            "type": "text",
                            "text": content_item["text"],
                            "cache_control": {
                                "type": "ephemeral"
                            }
                        })
                user_message["content"] = content_with_cache
            
            # Get model parameters or use defaults
            params = model_params or self.model_params or {}
            max_tokens = params.get("max_tokens", 2048)
            temperature = params.get("temperature", 0.5)
            top_p = params.get("top_p", 0.8)
            top_k = params.get("top_k", 250)
            stop_sequences = params.get("stop_sequences")
            
            # Prepare the request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "system": "Reply concisely",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k
            }
            
            # Add stop sequences if provided
            if stop_sequences:
                request_body["stop_sequences"] = stop_sequences
            
            # Print request details
            print("\nSending request to Claude model:")
            print(f"  - Using invoke_model API with model: {model_id}")
            print("  - Cache control set to 'ephemeral' for the question")
            
            response = runtime_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_data = json.loads(response['body'].read())
            
            # Check for cache metrics
            input_tokens = response_data["usage"].get("input_tokens", 0)
            output_tokens = response_data["usage"].get("output_tokens", 0)
            cache_read = response_data["usage"].get("cache_read_input_tokens", 0)
            cache_write = response_data["usage"].get("cache_creation_input_tokens", 0)
            
            if cache_read > 0:
                total_input_tokens = input_tokens + cache_read
                print("\n✅ CACHE HIT: Content was retrieved from cache")
                print(f"  - Cache read tokens: {cache_read}")
                print(f"  - {(cache_read / total_input_tokens * 100):.1f}% of input prompt cached ({total_input_tokens} tokens)")
            elif cache_write > 0:
                print("\n📝 CACHE WRITE: Content was written to cache")
                print(f"  - Cache write tokens: {cache_write}")
            else:
                print("\n❌ NO CACHE: No caching occurred")
            
            return response_data
            
        # For Amazon Nova models and other models that use converse API
        else:
            # Format messages for Nova models
            nova_messages = []
            
            # Process each message to create proper Nova format
            for msg in messages:
                if msg["role"] == "user":
                    # Create a new content array without "type" field
                    nova_content = []
                    
                    # Process each content item - ensure document content is preserved
                    for i, content_item in enumerate(msg["content"]):
                        if "type" in content_item and content_item["type"] == "text":
                            # Convert Claude format to Nova format
                            nova_content.append({
                                "text": content_item["text"]
                            })
                        elif "text" in content_item:
                            # Already in Nova format or simple text
                            nova_content.append({
                                "text": content_item["text"]
                            })
                    
                    # Add cachePoint between context and question if there are multiple content items
                    if len(nova_content) > 1:
                        nova_content.insert(1, {
                            "cachePoint": {
                                "type": "default"
                            }
                        })
                    
                    # Add the properly formatted user message
                    nova_messages.append({
                        "role": "user",
                        "content": nova_content
                    })
                elif msg["role"] == "assistant":
                    # Create assistant message with proper format
                    nova_content = []
                    for content_item in msg["content"]:
                        if "type" in content_item and content_item["type"] == "text":
                            # Convert Claude format to Nova format
                            nova_content.append({
                                "text": content_item["text"]
                            })
                        elif "text" in content_item:
                            # Already in Nova format or simple text
                            nova_content.append({
                                "text": content_item["text"]
                            })
                    
                    nova_messages.append({
                        "role": "assistant",
                        "content": nova_content
                    })
            
            # Print request details
            print("\nSending request to Amazon Nova model:")
            print(f"  - Using converse API with model: {model_id}")
            print("  - cachePoint inserted between context and question")
            
            # Get model parameters or use defaults
            params = model_params or self.model_params or {}
            max_tokens = params.get("max_tokens", 300)
            temperature = params.get("temperature", 0.3)
            top_p = params.get("top_p", 0.1)
            
            # Create system message for Nova models
            system_message = [{
                "text": "Reply Concisely"
            }]
            
            # Call Bedrock with converse API for Nova models
            response = runtime_client.converse(
                modelId=model_id,
                messages=nova_messages,
                system=system_message,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                }
            )
            
            # Process response
            output_message = response["output"]["message"]
            response_text = output_message["content"][0]["text"]
            
            # Create response_data in the same format as invoke_model would return
            response_data = {
                "content": [{"text": response_text}],
                "usage": response["usage"]
            }
            
            # Check for cache metrics
            input_tokens = response_data["usage"].get("inputTokens", 0)
            output_tokens = response_data["usage"].get("outputTokens", 0)
            cache_read = response_data["usage"].get("cacheReadInputTokens", 0)
            cache_write = response_data["usage"].get("cacheWriteInputTokens", 0)
            
            if cache_read > 0:
                total_input_tokens = input_tokens + cache_read
                print("\n✅ CACHE HIT: Content was retrieved from cache")
                print(f"  - Cache read tokens: {cache_read}")
                print(f"  - {(cache_read / total_input_tokens * 100):.1f}% of input prompt cached ({total_input_tokens} tokens)")
            elif cache_write > 0:
                print("\n📝 CACHE WRITE: Content was written to cache")
                print(f"  - Cache write tokens: {cache_write}")
            else:
                print("\n❌ NO CACHE: No caching occurred")
            
            return response_data
    
    def save_results(self, filename="cache_experiment_results.csv"):
        """Save experiment results to CSV file
        
        Args:
            filename: Name of the CSV file to save results to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.all_experiments_data:
                print("No experiment data to save.")
                return False
                
            pd.DataFrame(self.all_experiments_data).to_csv(filename, index=False)
            print(f"Results saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            return False
    
    def get_experiment_summary(self):
        """Get experiment summary statistics as a formatted string
        
        This method analyzes all collected experiment data and generates
        a comprehensive summary of the results, including:
        - Statistical analysis of token usage and latency
        - Cache hit rate calculation
        - Overall experiment metrics
        
        Returns:
            Formatted string with experiment summary statistics
            that can be displayed to users or logged
        """
        if not self.all_experiments_data:
            return "No experiment data available."
            
        df = pd.DataFrame(self.all_experiments_data)
        
        # Calculate cache hit information
        cache_hits = sum(1 for data in self.all_experiments_data if data.get("is_cache_hit", False))
        total_turns = len(self.all_experiments_data)
        hit_rate = (cache_hits / total_turns * 100) if total_turns > 0 else 0
        
        # Calculate timing information
        avg_latency = df["invocation_latency"].mean() if "invocation_latency" in df.columns else 0
        min_latency = df["invocation_latency"].min() if "invocation_latency" in df.columns else 0
        max_latency = df["invocation_latency"].max() if "invocation_latency" in df.columns else 0
        
        # Calculate average times for cache hits vs misses
        if cache_hits > 0 and (total_turns - cache_hits) > 0:
            cache_hit_times = [data["invocation_latency"] for data in self.all_experiments_data if data.get("is_cache_hit", False)]
            cache_miss_times = [data["invocation_latency"] for data in self.all_experiments_data if not data.get("is_cache_hit", False)]
            
            avg_hit_time = sum(cache_hit_times) / len(cache_hit_times) if cache_hit_times else 0
            avg_miss_time = sum(cache_miss_times) / len(cache_miss_times) if cache_miss_times else 0
            
            if avg_miss_time > 0:
                speedup = (avg_miss_time - avg_hit_time) / avg_miss_time * 100 if avg_miss_time > 0 else 0
        
        # Format the output with Markdown tables
        result = []
        result.append("## Experiment Results Summary")
        
        # Summary Statistics Table
        result.append("\n### Summary Statistics")
        result.append("| Metric | Mean | Median | Min | Max |")
        result.append("|--------|------|--------|-----|-----|")
        
        metrics = ["input_tokens", "output_tokens", "cache_creation_input_tokens", 
                  "cache_read_input_tokens", "invocation_latency"]
        
        for metric in metrics:
            if metric in df.columns:
                stats = df[metric].describe()
                result.append(f"| {metric.replace('_', ' ').title()} | {stats['mean']:.2f} | {stats['50%']:.2f} | {stats['min']:.2f} | {stats['max']:.2f} |")
        
        # Cache Performance Table
        result.append("\n### Cache Performance")
        result.append("| Metric | Value |")
        result.append("|--------|-------|")
        result.append(f"| Cache Hit Rate | {hit_rate:.1f}% ({cache_hits}/{total_turns} turns) |")
        result.append(f"| Total Turns | {total_turns} |")
        result.append(f"| Cache Hits | {cache_hits} |")
        result.append(f"| Cache Misses | {total_turns - cache_hits} |")
        
        # Timing Information Table
        result.append("\n### Timing Information")
        result.append("| Metric | Value (seconds) |")
        result.append("|--------|----------------|")
        result.append(f"| Average Response Time | {avg_latency:.2f} |")
        result.append(f"| Minimum Response Time | {min_latency:.2f} |")
        result.append(f"| Maximum Response Time | {max_latency:.2f} |")
        
        if cache_hits > 0 and (total_turns - cache_hits) > 0:
            result.append(f"| Average Time with Cache Hit | {avg_hit_time:.2f} |")
            result.append(f"| Average Time with Cache Miss | {avg_miss_time:.2f} |")
            if avg_miss_time > 0:
                result.append(f"| Cache Speedup | {speedup:.1f}% |")
        
        # Individual Turn Data Table
        result.append("\n### Individual Turn Data")
        result.append("| Turn | Question | Cache Hit | Input Tokens | Cache Read Tokens | Response Time (s) |")
        result.append("|------|----------|-----------|--------------|-------------------|-------------------|")
        
        for data in self.all_experiments_data:
            turn = data.get("turn", "N/A")
            question = data.get("question", "N/A")
            is_cache_hit = "✅" if data.get("is_cache_hit", False) else "❌"
            input_tokens = data.get("input_tokens", 0)
            cache_read = data.get("cache_read_input_tokens", 0)
            latency = data.get("invocation_latency", 0)
            
            # Truncate question if too long
            if len(question) > 30:
                question = question[:27] + "..."
                
            result.append(f"| {turn} | {question} | {is_cache_hit} | {input_tokens} | {cache_read} | {latency:.2f} |")
        
        return "\n".join(result)
    
    def get_turn_metrics(self, turn_data):
        """Get metrics for a specific turn as a formatted string
        
        This method formats the metrics for a single conversation turn
        into a human-readable string that can be displayed to users.
        It includes token usage, cache performance, and timing information.
        
        Args:
            turn_data: Dictionary containing the turn metrics from process_turn
            
        Returns:
            Formatted string with turn metrics ready for display
        """
        input_tokens = turn_data['input_tokens']
        output_tokens = turn_data['output_tokens']
        input_tokens_cache_read = turn_data['cache_read_input_tokens']
        input_tokens_cache_create = turn_data['cache_creation_input_tokens']
        elapsed_time = turn_data['invocation_latency']
        is_cache_hit = turn_data['is_cache_hit']
        turn_number = turn_data['turn']
        
        # Calculate the percentage of input prompt cached
        total_input_tokens = input_tokens + input_tokens_cache_read
        percentage_cached = (input_tokens_cache_read / total_input_tokens * 100) if total_input_tokens > 0 else 0
        
        # Format as markdown table
        metrics = []
        metrics.append(f"## Turn {turn_number} Metrics")
        
        # Cache status with emoji
        if is_cache_hit:
            metrics.append(f"### ✅ CACHE HIT")
        else:
            metrics.append(f"### ❌ CACHE MISS")
        
        # Timing table
        metrics.append("\n#### Timing Information")
        metrics.append("| Metric | Value |")
        metrics.append("|--------|-------|")
        metrics.append(f"| Start time | {time.strftime('%H:%M:%S', time.localtime(time.time() - elapsed_time))} |")
        metrics.append(f"| End time | {time.strftime('%H:%M:%S', time.localtime(time.time()))} |")
        metrics.append(f"| Response time | {elapsed_time:.2f} seconds |")
        
        # Token usage table
        metrics.append("\n#### Token Usage")
        metrics.append("| Metric | Value |")
        metrics.append("|--------|-------|")
        metrics.append(f"| User input tokens | {input_tokens} |")
        metrics.append(f"| Output tokens | {output_tokens} |")
        
        if is_cache_hit:
            metrics.append(f"| Cache read tokens | {input_tokens_cache_read} |")
            metrics.append(f"| Percentage cached | {percentage_cached:.1f}% of input prompt |")
            metrics.append(f"| Total input tokens | {total_input_tokens} |")
        else:
            metrics.append(f"| Cache write tokens | {input_tokens_cache_create} |")
        
        return "\n".join(metrics)
    
    def display_metrics(self):
        """Display all metrics including summary statistics and individual turn data
        
        Returns:
            True if metrics were displayed, False if no data available
        """
        if not self.all_experiments_data:
            print("No experiment data available.")
            return False
            
        try:
            # Print summary statistics
            print("\n===== Summary Statistics =====")
            df = pd.DataFrame(self.all_experiments_data)
            
            # Check for required columns
            required_columns = ["input_tokens", "output_tokens", "cache_creation_input_tokens", 
                              "cache_read_input_tokens", "invocation_latency"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"Warning: Missing columns in experiment data: {', '.join(missing_columns)}")
                # Use only available columns
                available_columns = [col for col in required_columns if col in df.columns]
                if available_columns:
                    print(df[available_columns].describe())
                else:
                    print("No metric columns available for summary statistics.")
            else:
                print(df[required_columns].describe())
            
            # Print cache hit information
            cache_hits = sum(1 for data in self.all_experiments_data if data.get("is_cache_hit", False))
            total_turns = len(self.all_experiments_data)
            hit_rate = (cache_hits / total_turns * 100) if total_turns > 0 else 0
            
            print(f"\n===== Cache Performance =====")
            print(f"Cache Hit Rate: {hit_rate:.1f}% ({cache_hits}/{total_turns} turns)")
            print(f"Total turns: {total_turns}")
            print(f"Cache hits: {cache_hits}")
            print(f"Cache misses: {total_turns - cache_hits}")
            
            # Print timing information
            print(f"\n===== Timing Information =====")
            avg_latency = df["invocation_latency"].mean() if "invocation_latency" in df.columns else "N/A"
            min_latency = df["invocation_latency"].min() if "invocation_latency" in df.columns else "N/A"
            max_latency = df["invocation_latency"].max() if "invocation_latency" in df.columns else "N/A"
            
            print(f"Average response time: {avg_latency:.2f} seconds")
            print(f"Minimum response time: {min_latency:.2f} seconds")
            print(f"Maximum response time: {max_latency:.2f} seconds")
            
            # Calculate average times for cache hits vs misses
            if cache_hits > 0 and (total_turns - cache_hits) > 0:
                cache_hit_times = [data["invocation_latency"] for data in self.all_experiments_data if data.get("is_cache_hit", False)]
                cache_miss_times = [data["invocation_latency"] for data in self.all_experiments_data if not data.get("is_cache_hit", False)]
                
                avg_hit_time = sum(cache_hit_times) / len(cache_hit_times) if cache_hit_times else 0
                avg_miss_time = sum(cache_miss_times) / len(cache_miss_times) if cache_miss_times else 0
                
                print(f"Average time with cache hit: {avg_hit_time:.2f} seconds")
                print(f"Average time with cache miss: {avg_miss_time:.2f} seconds")
                if avg_miss_time > 0:
                    print(f"Cache speedup: {(avg_miss_time - avg_hit_time) / avg_miss_time * 100:.1f}%")
            
            # Print individual turn data
            print("\n===== Individual Turn Data =====")
            print(df)
            
            return True
        except Exception as e:
            print(f"Error displaying metrics: {str(e)}")
            return False
    
    # Removed redundant print_results method that just called self.display_metrics()


class ExperimentManager:
    """Manages the creation and display of prompt caching experiments
    
    This class provides utility methods for creating properly configured
    experiments and displaying their results in a structured way.
    """
    
    @staticmethod
    def create_experiment():
        """Create and configure a PromptCachingExperiment with shared services
        
        This method creates the necessary services and experiment
        instance with proper dependency injection, ensuring that all components
        share the same service instances.
        
        Returns:
            Configured PromptCachingExperiment instance ready to use
            
        Raises:
            ImportError: If required modules are not available
            RuntimeError: If service initialization fails
        """
        try:
            # Create shared services
            bedrock_service = BedrockService()
            
            # Create model manager with the bedrock service
            model_manager = ModelManager(bedrock_service=bedrock_service)
            
            # Create experiment with shared services
            experiment = PromptCachingExperiment(
                bedrock_service=bedrock_service,
                model_manager=model_manager
            )
            
            return experiment
        except ImportError as e:
            raise ImportError(f"Required module not available: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to create experiment: {str(e)}")
    
    # Removed redundant display_experiment_results method that just called experiment.display_metrics()

if __name__ == "__main__":
    # Create experiment using the ExperimentManager
    experiment = ExperimentManager.create_experiment()
    
    # Default model
    default_model_name = "Claude 3.7 Sonnet"
    default_model = experiment.model_manager.get_model_arn_from_inference_profiles("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    
    # Load context text
    print("Select context source:")
    print("1. Load from file (RomeoAndJuliet.txt)")
    print("2. Enter file path")
    print("3. Enter URL")
    
    context_choice = input("Enter choice (1-3): ")
    
    if context_choice == "1":
        experiment.load_context_from_file("RomeoAndJuliet.txt")
    elif context_choice == "2":
        file_path = input("Enter file path: ")
        experiment.load_context_from_file(file_path)
    elif context_choice == "3":
        url = input("Enter URL: ")
        experiment.load_context_from_url(url)
    else:
        print("Invalid choice. Using default Romeo and Juliet text.")
        experiment.load_context_from_file("RomeoAndJuliet.txt")
    
    # Ask user which mode to run
    print("\nSelect mode:")
    print("1. Run predefined experiment")
    print("2. Interactive chat mode")
    print("3. Interactive chat mode (with metrics on demand)")
    
    choice = input("Enter choice (1-3): ")
    
    # Model selection
    print("\nSelect model:")
    print(f"1. Use default model [{default_model_name}]")
    print("2. Select from available models")
    
    model_choice = input("Enter choice (1-2): ")
    
    if model_choice == "1":
        model_id = default_model
        print(f"Using default model: {default_model} [{default_model_name}]")
    elif model_choice == "2":
        # Add default model to the model list for selection
        if "Anthropic Claude Models" in experiment.model_manager.models:
            if default_model not in experiment.model_manager.models["Anthropic Claude Models"]:
                experiment.model_manager.models["Anthropic Claude Models"].append(default_model)
        model_id = experiment.model_manager.select_model()
    else:
        print(f"Invalid choice. Using default model: {default_model} [{default_model_name}]")
        model_id = default_model
    
    if choice == "1":
        # Run predefined experiment
        experiment.run_experiments(n_experiments=1, n_turns=6, model_id=model_id)
        # Display experiment results
        experiment.display_metrics()
    elif choice == "2":
        # Interactive chat with metrics after each turn
        experiment.interactive_chat(model_id=model_id)
        # Display final experiment summary
        experiment.display_metrics()
    elif choice == "3":
        # Interactive chat with metrics on demand (using 'stats' command)
        print("\nType 'stats' during chat to see current metrics")
        experiment.interactive_chat(model_id=model_id)
        # Display final experiment summary
        experiment.display_metrics()
    else:
        print("Invalid choice. Exiting.")