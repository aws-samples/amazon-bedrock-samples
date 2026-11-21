"""
Amazon Bedrock Prompt Router Chat Application

This module provides a command-line interface for interacting with Amazon Bedrock
using prompt routers. It tracks usage statistics and allows switching between
different prompt routers.
"""
import json
import boto3
import os
import time
from file_processor import FileProcessor


class UsageStats:
    """
    Tracks and calculates token usage statistics for chat interactions.
    
    This class maintains counters for input/output tokens, calculates rates,
    and provides reporting functionality.
    """
    def __init__(self):
        # Initialize counters and tracking variables
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_chats = 0
        self.start_time = time.time()
        self.model_invocations = {}
        
    def calculate_tokens(self, text):
        """
        Calculate approximate number of tokens in text.
        
        Args:
            text (str): The text to calculate tokens for
            
        Returns:
            int: Estimated token count (based on 4 chars per token)
        """
        # Simple token estimation (average 4 chars per token)
        return max(1, len(text.strip()) // 4)
        
    def track_usage(self, input_text, output_text, model_used=None):
        """
        Track token usage for a single chat interaction.
        
        Args:
            input_text (str): User input text
            output_text (str): Model response text
            model_used (str, optional): Name of the model used
            
        Returns:
            dict: Usage statistics for the current interaction
        """
        # Calculate token counts
        input_tokens = self.calculate_tokens(input_text)
        output_tokens = self.calculate_tokens(output_text)
        
        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_chats += 1
        
        # Track model invocations
        if model_used:
            self.model_invocations[model_used] = self.model_invocations.get(model_used, 0) + 1
        
        # Calculate rates
        elapsed_minutes = max(0.1, (time.time() - self.start_time) / 60)
        tpm = (input_tokens + output_tokens) / elapsed_minutes
        rpm = self.total_chats / elapsed_minutes
        
        # Print current interaction stats
        print("\nUsage Statistics (Current Interaction):")
        print("-" * 50)
        print(f"{'Metric':<20} {'Count':<15} {'Details'}")
        print("-" * 50)
        print(f"{'Input Tokens':<20} {input_tokens:<15} (Approximate)")
        print(f"{'Output Tokens':<20} {output_tokens:<15} (Approximate)")
        print(f"{'Total Tokens':<20} {input_tokens + output_tokens:<15}")
        print(f"{'TPM':<20} {tpm:>15.2f} (Tokens/minute)")
        print(f"{'RPM':<20} {rpm:>15.2f} (Requests/minute)")
        if model_used:
            print(f"{'Model Used':<20} {model_used:<15} ({self.model_invocations[model_used]} invocations)")
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'tpm': tpm,
            'rpm': rpm
        }
    
    def print_total_stats(self):
        """
        Print comprehensive usage statistics for the entire session.
        """
        elapsed_minutes = max(0.1, (time.time() - self.start_time) / 60)
        total_tokens = self.total_input_tokens + self.total_output_tokens
        avg_tokens_per_chat = total_tokens / max(1, self.total_chats)
        tpm = total_tokens / elapsed_minutes
        rpm = self.total_chats / elapsed_minutes
        
        print("\nTotal Usage Statistics:")
        print("=" * 60)
        print(f"{'Metric':<25} {'Count':<15} {'Details'}")
        print("=" * 60)
        print(f"{'Total Chats':<25} {self.total_chats:<15}")
        print(f"{'Total Input Tokens':<25} {self.total_input_tokens:<15} (Approximate)")
        print(f"{'Total Output Tokens':<25} {self.total_output_tokens:<15} (Approximate)")
        print(f"{'Total Tokens':<25} {total_tokens:<15}")
        print(f"{'Avg Tokens per Chat':<25} {avg_tokens_per_chat:>15.2f}")
        print(f"{'Overall TPM':<25} {tpm:>15.2f} (Tokens/minute)")
        print(f"{'Overall RPM':<25} {rpm:>15.2f} (Requests/minute)")
        print(f"{'Session Duration':<25} {elapsed_minutes:>15.2f} (Minutes)")
        if self.model_invocations:
            print("\nModel Invocations:")
            for model, count in self.model_invocations.items():
                print(f"{'- ' + model:<25} {count:<15} invocations")
        print("=" * 60)


class ChatSession:
    """
    Manages a chat session with Amazon Bedrock.
    
    Handles message history, sending messages to Bedrock, and processing responses.
    """
    def __init__(self, model_id=None, region="us-east-1"):
        # Initialize Bedrock client
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime",
            region_name=region
        )
        # Set default model ID or use provided one
        self.model_id = model_id or "anthropic.claude-sonnet-4-5-20250929-v1:0"
        # Initialize conversation history
        self.messages = []
        self.usage_stats = UsageStats()
        
    def add_message(self, content, role="user"):
        """
        Add a message to the conversation history.
        
        Args:
            content (str): Message content
            role (str): Message role (user or assistant)
        """
        self.messages.append({
            "role": role,
            "content": [{"text": content}]
        })
    
    def send_message(self, message=None):
        """
        Send a message to Bedrock and process the streaming response.
        
        Args:
            message (str, optional): User message to send
            
        Returns:
            tuple: (trace_data, model_used) - Routing trace data and model ID
        """
        if message:
            self.add_message(message)
        
        try:
            # Get streaming response from Bedrock
            response = self.bedrock_runtime.converse_stream(
                modelId=self.model_id,
                messages=self.messages
            )
            
            # Process the streaming response
            assistant_response = ""
            trace_data = None
            model_used = None
            
            print("\nAssistant: ", end="")
            for chunk in response["stream"]:
                if "contentBlockDelta" in chunk:
                    text = chunk["contentBlockDelta"]["delta"].get("text", "")
                    print(text, end="", flush=True)
                    assistant_response += text
                    
                if "metadata" in chunk:
                    if "trace" in chunk["metadata"]:
                        trace_data = chunk["metadata"]["trace"]
                        # Extract the model used from trace data
                        if "promptRouter" in trace_data and "invokedModelId" in trace_data["promptRouter"]:
                            full_model_id = trace_data["promptRouter"]["invokedModelId"]
                            # Extract just the model name after the last '/'
                            model_used = full_model_id.split('/')[-1] if '/' in full_model_id else full_model_id
                        elif "selectedRoute" in trace_data:
                            full_model_id = trace_data["selectedRoute"].get("modelId", "Unknown model")
                            model_used = full_model_id.split('/')[-1] if '/' in full_model_id else full_model_id
            
            print("\n")
            
            # Track usage statistics
            self.usage_stats.track_usage(message or "", assistant_response, model_used)
            
            if assistant_response:
                self.add_message(assistant_response, role="assistant")
            
            if not model_used:
                model_used = self.model_id
            
            return trace_data, model_used
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            return None, None


class PromptRouterManager:
    """
    Manages Amazon Bedrock prompt routers.
    
    Provides functionality to list, select, and get details about prompt routers.
    """
    def __init__(self, region="us-east-1"):
        self.bedrock = boto3.client('bedrock', region_name=region)
        self.region = region
        self.account_id = os.getenv('AWS_ACCOUNT_ID')
        
        # Try to get account ID if not provided in environment
        if not self.account_id:
            try:
                sts = boto3.client('sts')
                self.account_id = sts.get_caller_identity()['Account']
            except Exception as e:
                print(f"Warning: Could not determine AWS account ID: {e}")
                self.account_id = None
        
        # Initialize fallback routers for when API calls fail
        self.fallback_routers = self._get_fallback_routers()

    def _get_fallback_routers(self):
        """
        Get fallback routers configuration when API calls fail.
        
        Returns:
            list: List of default router configurations
        """
        if not self.account_id:
            return []
            
        return [
            {
                'name': 'anthropic.claude',
                'arn': f'arn:aws:bedrock:{self.region}:{self.account_id}:default-prompt-router/anthropic.claude:1',
                'provider': 'Anthropic',
                'type': 'default'
            },
            {
                'name': 'meta.llama',
                'arn': f'arn:aws:bedrock:{self.region}:{self.account_id}:default-prompt-router/meta.llama:1',
                'provider': 'Meta',
                'type': 'default'
            }
        ]

    def extract_provider_and_name(self, router_arn):
        """
        Extract provider and name from router ARN.
        
        Args:
            router_arn (str): The ARN of the prompt router
            
        Returns:
            tuple: (provider, router_name) - Provider and name extracted from ARN
        """
        provider = 'Unknown'
        router_name = 'Default Router'
        
        # Extract provider from ARN
        if 'anthropic' in router_arn.lower():
            provider = 'Anthropic'
        elif 'meta' in router_arn.lower() or 'llama' in router_arn.lower():
            provider = 'Meta'
        elif 'cohere' in router_arn.lower():
            provider = 'Cohere'
        elif 'ai21' in router_arn.lower():
            provider = 'AI21'
        elif 'mistral' in router_arn.lower():
            provider = 'Mistral'
        elif 'amazon' in router_arn.lower():
            provider = 'Amazon'
        else:
            # For unknown providers, extract from ARN
            parts = router_arn.split('/')
            if len(parts) > 1:
                model_part = parts[-1].split(':')[0]
                if '.' in model_part:
                    provider = model_part.split('.')[0].capitalize()
        
        # For unknown router names, use the model part from ARN
        parts = router_arn.split('/')
        if len(parts) > 1:
            router_name = parts[-1].split(':')[0]
        
        return provider, router_name

    def get_prompt_routers(self):
        """
        Get all available prompt routers in Bedrock.
        
        Returns:
            list: List of prompt router configurations
        """
        prompt_routers = []
        
        try:
            # Get custom prompt routers
            try:
                custom_routers = self.bedrock.list_prompt_routers(type='custom', maxResults=100)
                for router in custom_routers.get('promptRouterSummaries', []):
                    router_arn = router.get('promptRouterArn', '')
                    router_name = router.get('promptRouterName', 'Custom Router')
                    
                    provider, extracted_name = self.extract_provider_and_name(router_arn)
                    
                    if router_name == 'Custom Router':
                        router_name = extracted_name
                    
                    prompt_routers.append({
                        'name': router_name,
                        'arn': router_arn,
                        'provider': provider,
                        'type': 'custom'
                    })
            except Exception as e:
                print(f"Could not fetch custom prompt routers: {str(e)}")
            
            # Get default prompt routers
            try:
                default_routers = self.bedrock.list_prompt_routers(type='default', maxResults=100)
                for router in default_routers.get('promptRouterSummaries', []):
                    router_arn = router.get('promptRouterArn', '')
                    router_name = router.get('promptRouterName', 'Default Router')
                    
                    provider, extracted_name = self.extract_provider_and_name(router_arn)
                    
                    if router_name == 'Default Router':
                        router_name = extracted_name
                    
                    prompt_routers.append({
                        'name': router_name,
                        'arn': router_arn,
                        'provider': provider,
                        'type': 'default'
                    })
            except Exception as e:
                print(f"Could not fetch default prompt routers: {str(e)}")
                if self.fallback_routers:
                    prompt_routers.extend(self.fallback_routers)
            
            return prompt_routers
        
        except Exception as e:
            print(f"Error fetching prompt routers: {str(e)}")
            return self.fallback_routers if self.fallback_routers else []

    def get_router_details(self, router_arn):
        """
        Get details of a prompt router including supported models.
        
        Args:
            router_arn (str): The ARN of the prompt router
            
        Returns:
            dict: Router details including supported models
        """
        try:
            response = self.bedrock.get_prompt_router(promptRouterArn=router_arn)
            
            # Extract supported models
            supported_models = []
            if 'models' in response:
                for model in response['models']:
                    if 'modelArn' in model:
                        model_arn = model['modelArn']
                        if '/' in model_arn:
                            model_id = model_arn.split('/')[-1]
                            supported_models.append(model_id)
            
            # Add fallback model if present
            if 'fallbackModel' in response and 'modelArn' in response['fallbackModel']:
                fallback_arn = response['fallbackModel']['modelArn']
                if '/' in fallback_arn:
                    fallback_id = fallback_arn.split('/')[-1]
                    if fallback_id not in supported_models:
                        supported_models.append(fallback_id)
            
            return {
                'name': response.get('promptRouterName', ''),
                'description': response.get('description', ''),
                'supported_models': supported_models,
                'type': response.get('type', '')
            }
        except Exception as e:
            print(f"Could not fetch router details for {router_arn}: {str(e)}")
            return {
                'name': '',
                'description': '',
                'supported_models': [],
                'type': ''
            }

    def select_prompt_router(self):
        """
        Display available prompt routers and let user select one.
        
        Returns:
            str: ARN of the selected prompt router or None if no selection
        """
        routers = self.get_prompt_routers()
        
        if not routers:
            print("No prompt routers available.")
            return None
        
        print("\nAvailable Prompt Routers:")
        print("-" * 60)
        print(f"{'#':<3} {'Name':<25} {'Provider':<10} {'Type':<10}")
        print("-" * 60)
        
        for i, router in enumerate(routers):
            print(f"{i+1:<3} {router['name']:<25} {router['provider']:<10} {router['type']:<10}")
        
        while True:
            try:
                choice = input("\nSelect a prompt router (number) or press Enter for default: ")
                if not choice:
                    return routers[0]['arn']
                
                choice = int(choice)
                if 1 <= choice <= len(routers):
                    return routers[choice-1]['arn']
                else:
                    print(f"Please enter a number between 1 and {len(routers)}")
            except ValueError:
                print("Please enter a valid number")


def main():
    """
    Main function to run the Bedrock Prompt Router Chat application.
    """
    print("Bedrock Prompt Router Chat")
    print("=" * 50)
    
    # Get region from environment or use default
    region = os.getenv('AWS_REGION', 'us-east-1')
    router_manager = PromptRouterManager(region=region)
    
    print("\nFetching available prompt routers...")
    router_arn = router_manager.select_prompt_router()
    
    # Set up model ID based on router selection
    if not router_arn:
        print("Using default model as no router was selected.")
        model_id = os.getenv('BEDROCK_MODEL_ID', "anthropic.claude-sonnet-4-5-20250929-v1:0")
    else:
        model_id = router_arn
        router_details = router_manager.get_router_details(model_id)
        print(f"\nUsing prompt router: {model_id}")
        if router_details['supported_models']:
            print("\nSupported Models:")
            for model in router_details['supported_models']:
                print(f"- {model}")
    
    # Initialize chat session
    chat = ChatSession(model_id=model_id, region=region)
    
    # Display welcome message and commands
    print("\nWelcome to the Bedrock Chat!")
    print("Commands:")
    print("- Type 'exit' or 'quit' to end the chat")
    print("- Type 'trace' to toggle routing information")
    print("- Type 'router' to switch prompt routers")
    print("- Type 'models' to see supported models for current router")
    print("- Type 'stats' to see total usage statistics")
    print("- Type 'upload' to process a file (PDF, DOCX, or TXT)\n")
    
    # Main chat loop
    show_trace = False
    while True:
        user_input = input("You: ").strip()
        
        # Handle exit command
        if user_input.lower() in ["exit", "quit"]:
            chat.usage_stats.print_total_stats()
            print("\nGoodbye!")
            break
        
        # Handle trace command    
        if user_input.lower() == "trace":
            show_trace = not show_trace
            print(f"Trace display: {'ON' if show_trace else 'OFF'}")
            continue
        
        # Handle router command
        if user_input.lower() == "router":
            new_router_arn = router_manager.select_prompt_router()
            if new_router_arn:
                chat.model_id = new_router_arn
                print(f"\nSwitched to prompt router: {new_router_arn}")
            continue
        
        # Handle models command    
        if user_input.lower() == "models":
            router_details = router_manager.get_router_details(chat.model_id)
            if router_details['supported_models']:
                print("\nSupported Models:")
                for model in router_details['supported_models']:
                    print(f"- {model}")
            else:
                print("No model information available for this router")
            continue
        
        # Handle stats command    
        if user_input.lower() == "stats":
            chat.usage_stats.print_total_stats()
            continue
        
        # Handle file upload command    
        if user_input.lower() == "upload":
            print("\nEnter the path to your file (PDF, DOCX, or TXT):")
            file_path = input().strip()
            
            if not os.path.exists(file_path):
                print("File not found. Please check the path and try again.")
                continue
                
            try:
                import io
                with open(file_path, 'rb') as file:
                    file_content = file.read()
                    uploaded_file = io.BytesIO(file_content)
                    uploaded_file.name = os.path.basename(file_path)
                    
                    if not FileProcessor.is_supported_file(uploaded_file.name):
                        print("Unsupported file type. Please upload a PDF, DOCX, or TXT file.")
                        continue
                    
                    print("Processing file...")
                    extracted_text = FileProcessor.process_uploaded_file(uploaded_file)
                    
                    if extracted_text:
                        print("\nFile content extracted successfully. Sending to chat...")
                        trace, model_used = chat.send_message(extracted_text)
                    else:
                        print("Could not extract text from the file.")
                    continue
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                continue
        
        # Process regular chat message
        trace, model_used = chat.send_message(user_input)
        
        if trace is None:
            continue
            
        print(f"\n[Response generated by: {model_used}]")
        
        # Display trace information if enabled
        if show_trace and trace:
            print("\nRouting Trace:")
            if "promptRouter" in trace and "invokedModelId" in trace["promptRouter"]:
                full_model_id = trace["promptRouter"]["invokedModelId"]
                model_name = full_model_id.split('/')[-1]
                print(f"Model Used: {model_name}")
            else:
                print(json.dumps(trace, indent=2))


if __name__ == "__main__":
    main()