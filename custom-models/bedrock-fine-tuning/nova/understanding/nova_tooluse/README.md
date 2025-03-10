# Amazon Nova Tool Use Finetuning with Amazon Bedrock

## Description
This repository demonstrates how to perform fine-tuning with the Amazon Nova models for tool usage using Amazon Bedrock. 

## Installation
Please install dependencies using the requirements.txt file
`pip install -r requirements.txt`

## Usage
There are three notebooks:

1. 01_toolcall_nova_bedrock_invokeAPI_and_converseAPI_.ipynb : Playground to use bedrock invoke and converse api for tool use with predefined set of tools. This notebook shows how the tool config, prompt and messages API should look like to align with bedrock converse API and bedrock invoke API. You can check how they work by using different input questions.

2. 02_script_tool_dataset_to_bedrock_nova_ft.ipynb: This script  converts the dataset originally intended for Llama ft with huggingface, to dataset format to align with the format required by Amazon Nova for finetuning using Amazon Bedrock invoke api. 

3. 03_toolcall_fullfinetune_nova_bedrock.ipynb: Script to setup the IAM roles with the s3 bucket with data and creating a new finetuning job with Amazon Nova using bedrock API. Note that finetuning can be done directly from Amazon Bedrocj console as well.

4. 04_toolcall_test_inference_finetuned_nova_bedrock.ipynb: Inference script to deploy your finetuned model using provisioned throughput, load your finetuned model and run inference with it. The script also calculates the accuracy metrics on validation set for both tool usage and args calling. 

## Support
Reach out to baishch@

## Roadmap


## Contributing
Contributions are welcome! Reach out to baishch@

## Authors and acknowledgment
baishch@

## License
MIT-0