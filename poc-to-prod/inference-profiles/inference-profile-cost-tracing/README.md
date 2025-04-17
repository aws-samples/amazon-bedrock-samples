# AWS Inference Profile Cost Tracing

This project automates the process of creating and setting up AWS Inference Profiles with cost tracing and monitoring capabilities. It leverages tags and custom CloudWatch dashboards to allow customers to monitor their usage and costs associated with invoking large language models (LLMs) from Anthropic's Bedrock service.

## Project Overview

The project operates based on a configuration file (`config.json`) that defines the AWS resources to be created, such as Inference Profiles, IAM roles, CloudWatch dashboards, and SNS topics for alerts. Each Inference Profile contains a set of tags that represent attributes like the customer account, application ID, model name, and environment.

When invoking an LLM through the deployed API Gateway, the project automatically associates the request with the appropriate Inference Profile based on the provided tags. It then publishes metrics to CloudWatch, including token counts and costs, enabling cost tracking and monitoring at a granular level.

## Getting Started
Prerequisite: You have a local machine/IDE with access to a terminal. The steps outlined will refer to your IDE but this can be done in a wide variety of environments.

1. Open a terminal in your IDE (the commands in quotes in the following steps can be typed/copy&pasted into the terminal (without the quotes)).
2. Create python virtual environment: "python -m venv .venv".
3. Activate environment on Windows: ".venv\Scripts\activate" || Activate environment on Mac: "source .venv/bin/activate".
4. Clone Repo: "git clone https://github.com/aws-samples/amazon-bedrock-samples.git".
5. Move to the correct directory: "cd amazon-bedrock-samples/poc-to-prod/inference-profiles/inference-profile-cost-tracing".
6. Install dependencies: "pip install -r requirements.txt".
7. Configure your AWS credentials: "aws configure" (this will ask you for your Access Key ID, Secret Access Key ID, AWS Region, and Default output format (can be kept as "None"))
9. Modify the `config.json` file to suit your requirements (Inference Profile tags, cost thresholds, SNS email, Lambda Role).
10. (THIS STEP IS REQUIRED IF YOU ARE ON A WINDOWS MACHINE. CAN BE IGNORED OTHERWISE). Open "utils.py" in the "scripts" folder, and follow the comments on line 35 & 39 (configuring an S3 bucket).
11. (THIS STEP IS REQUIRED IF YOU ARE ON A WINDOWS MACHINE. CAN BE IGNORED OTHERWISE). In the "config" folder you will find "config.json" & "models.json" upload these to the S3 bucket you have specified in the previous step (step 10).
12. Run the `setup.py` script to create and deploy all necessary AWS resources: "python setup.py".
13. After the setup is complete, you can invoke the LLM through the deployed API Gateway, passing the required headers (e.g., `inference-profile-id`, `region`, `tags`).

## Monitoring and Alerting

The project creates a custom CloudWatch dashboard named `BedrockInvocationDashboard` to visualize the metrics related to LLM invocations and costs. Additionally, it sets up an SNS topic (`BedrockInvocationAlarms`) to receive email alerts based on configurable thresholds for cost, token usage, and request counts.

## Customization

You can easily extend or modify the project to suit your specific needs. For example, you could add support for additional LLM providers, customize the dashboard layout, or integrate with other monitoring and alerting systems.

## Contributing

Contributions to this project are welcome. If you encounter any issues or have ideas for improvements, please open an issue or submit a pull request.
