# Amazon Bedrock Prompt Caching and Routing Workshop

This repository contains a complete implementation of Amazon Bedrock's prompt caching and routing capabilities using the latest Claude 4.5 models.

## Features

- **Prompt Caching**: Reduce latency and costs by caching frequently used prompts
- **Prompt Routing**: Intelligently route requests to optimal models
- **Latest Models**: Updated to use Claude Haiku 4.5, Sonnet 4.5, and Opus 4.1
- **Global Endpoints**: Compatible across all AWS regions
- **Multiple Interfaces**: Both CLI and Streamlit web applications

## Project Structure

```
BedrockPromptDemo/
├── src/
│   ├── bedrock_prompt_caching.py    # CLI application for prompt caching
│   ├── bedrock_prompt_routing.py    # CLI application for prompt routing
│   ├── prompt_caching_app.py        # Streamlit UI for prompt caching
│   ├── prompt_router_app.py         # Streamlit UI for prompt routing
│   ├── model_manager.py             # Model selection and management
│   ├── bedrock_service.py           # Bedrock API service wrapper
│   └── file_processor.py            # File processing utilities
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Latest Models Supported

- **Claude Haiku 4.5**: `anthropic.claude-haiku-4-5-20251001-v1:0`
- **Claude Sonnet 4.5**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Claude Opus 4.1**: `anthropic.claude-opus-4-1-20250805-v1:0`
- **Amazon Nova Models**: `amazon.nova-micro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-pro-v1:0`

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.8+
- Access to Amazon Bedrock with Claude models enabled

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd BedrockPromptDemo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure AWS credentials:
```bash
aws configure
```

## Usage

### CLI Applications

**Prompt Caching:**
```bash
cd src
python bedrock_prompt_caching.py
```

**Prompt Routing:**
```bash
cd src
python bedrock_prompt_routing.py
```

### Web Applications

**Prompt Caching UI:**
```bash
cd src
streamlit run prompt_caching_app.py
```

**Prompt Routing UI:**
```bash
cd src
streamlit run prompt_router_app.py
```

## Key Features

### Prompt Caching
- Automatically caches document context for faster subsequent queries
- Shows cache hit/miss statistics
- Demonstrates cost and latency benefits
- Supports multi-turn conversations

### Prompt Routing
- Intelligently routes requests to optimal models
- Displays routing decisions and model selection
- Tracks usage statistics across different models
- Supports file uploads (PDF, DOCX, TXT)

### Model Management
- Dynamic model selection from available Bedrock models
- Inference profile resolution for optimal performance
- Fallback model configuration
- Global endpoint support for multi-region compatibility

## Configuration

The applications use global model endpoints by default, making them compatible across all AWS regions. Models are automatically resolved to regional endpoints by Bedrock's routing service.

## Workshop Learning Objectives

This code demonstrates:
1. How to implement prompt caching to reduce costs and latency
2. How to use prompt routing for intelligent model selection
3. Best practices for Bedrock API integration
4. Performance monitoring and usage tracking
5. Multi-modal file processing capabilities

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.