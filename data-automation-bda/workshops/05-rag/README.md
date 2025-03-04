---
chapter: true
title: Lab - Amazon Bedrock Data Automation (BDA) Parser for Document, Image Audio and Video files
weight: 20
---

In this module, you'll learn how to use Amazon Bedrock Data Automation (BDA) to parse document, image, audio and video content and create a Multimodal Retrieval-Augmented Generation (RAG) Application with Amazon Bedrock Knowledge Bases. This module contains:

1. Overview
2. Pre-requisites
3. How to process document, image, audio and video content with BDA
3. How to create a knowledge base with BDA outputs for audio and video content
4. How to query and analyze document, audio and video content

## Overview
The module is designed to analyze and generate insights from multi-modalal data, including textual, visual, video and audio data. By incorporating contextual information from your own data sources with BDA, you can create highly accurate embedding for multi-modal data with Bedrock Knowledge Bases and secure intelligent search Generative AI applications.

### BDA for Multi-Modality Processing
BDA is a managed service that automatically extracts content from multimodal data. BDA streamlines the generation of valuable insights from unstructured multimodal content such as documents, images, audio, and videos through a unified multi-modal inference API.

### Document and Image Analysis
- Text extraction and template detection to seperate images and tables
- Detailed summaries of document and image files
- Content moderation and safety checks
- Image metadata extraction
- Flexible Customer Blueprint to extract Insights from documents and images 
- Seamless integration with Bedrock Knowledge Bases

### Audio Content Analysis
BDA provides comprehensive audio analysis capabilities, automatically extracting:
- Detailed audio summaries
- Turn-by-turn transcripts with speaker identification
- Speaker diarization (who spoke when)
- Content moderation scores
- Audio file metadata
- Speech and music detection
- Background noise analysis

### Video Content Analysis
Amazon Bedrock Data Automation (BDA) allows you to transform unstructured video content into structured, queryable data. The service automatically extracts key information such as:
- Shot segmentation with timestamps
- Video transcripts
- Scene summaries
- Visual content descriptions

### Knowledge Base Integration
The extracted audio, video and document information is stored in a knowledge base that can be queried using natural language. This allows you to:
- Search for specific moments in audio and videos
- Search for specific document information and images
- Extract timestamps and segments
- Get detailed summaries of document, image, audio and video content
- Access audio and video metadata and playback information

#### Notes:

- Please make sure to enable Anthropic Claude 3 Sonnet and  Titan Text Embeddings V2 model access in Amazon Bedrock Console before running this notebook. 

## Pre-requisites
Before running this notebook, ensure you have:
1. Access to Amazon Bedrock and appropriate permissions
2. Required Python packages installed (boto3, json, IPython.display)

![BDA video and audio with KB Architecture](/static/bda_kb_integration.png)

## Try it out
### At an AWS Event
If you are following the workshop via workshop studio, go to your `SageMaker Studio Domain` and navigate to `SageMaker Studio Classic` under the `sagemakeruser` user.

In the SageMaker Studio Classic UI navigate to `knowledge-bases-for-bedrock-workshop/bda_kb/bda_kb.ipynb`

### Self-paced
You can access the notebook directly from our GitHub repository: [BDA Knowledge Base Notebook](https://github.com/aws-samples/rag-workshop-amazon-bedrock-knowledge-bases/blob/main/bda_kb/bda_kb.ipynb).
