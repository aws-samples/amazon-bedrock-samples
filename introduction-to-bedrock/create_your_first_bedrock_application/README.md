
# Create your first Amazon Bedrock generative AI application

This repository contains the code for deploying your first application with [Amazon Bedrock](https://aws.amazon.com/bedrock/) using [AWS CDK](https://aws.amazon.com/cdk/)

For this exercise, we will create and application that processes the text content from emails and extract information from them.
For simplicity and in order to ensure compatibility with multiple customer setups, two options are presented:

* **process-dynamodb-table-bedrock:** assumes that your emails have been extracted to a dynamoDB and are indexed via `thread_id`. This option is useful for the cases where you already have the emails extraction workflow connected to an existent pipeline, and you would like to extract the information from existent data


* **process-emails-bedrock:** connects to your email service using [Amazon Simple Email Service (SES)](https://aws.amazon.com/ses/) and [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/) to process new emails that are sent to a certain email box. This option is specially interesting for cases where a central email address is used to connect customers to a certain business.


Both options process the emails using [AWS Lambda](https://aws.amazon.com/lambda/) to query Bedrock. To get started, select your preferred solution and follow the intructions of the `README.md` file of the respective folder. 

For educational purposes, the notebook `GettingStartedWithAmazonBedrock.ipynb` provides examples of how to get started with Amazon Bedrock, invoking different models and applying prompt engineering techniques. 