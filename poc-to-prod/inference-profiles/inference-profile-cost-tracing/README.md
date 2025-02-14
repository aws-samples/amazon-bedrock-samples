# AWS Inference Profile Cost Tracing

This project automates the process of creating and setting up AWS Inference Profiles with cost tracing and monitoring capabilities. It leverages tags and custom CloudWatch dashboards to allow customers to monitor their usage and costs associated with invoking large language models (LLMs) from Anthropic's Bedrock service.

## Project Overview

The project operates based on a configuration file (`config.json`) that defines the AWS resources to be created, such as Inference Profiles, IAM roles, CloudWatch dashboards, and SNS topics for alerts. Each Inference Profile contains a set of tags that represent attributes like the customer account, application ID, model name, and environment.

When invoking an LLM through the deployed API Gateway, the project automatically associates the request with the appropriate Inference Profile based on the provided tags. It then publishes metrics to CloudWatch, including token counts and costs, enabling cost tracking and monitoring at a granular level.

## Getting Started

1. Clone the repository to your local machine.
2. Install the required dependencies (e.g., AWS CLI, Python libraries).
3. Configure your AWS credentials and region.
4. Modify the `config.json` file to suit your requirements (e.g., Inference Profile tags, cost thresholds, SNS email).
5. Run the `setup.py` script to create and deploy all necessary AWS resources.

```
python setup.py
```

6. After the setup is complete, you can invoke the LLM through the deployed API Gateway, passing the required headers (e.g., `inference-profile-id`, `region`, `tags`).

## Monitoring and Alerting

The project creates a custom CloudWatch dashboard named `BedrockInvocationDashboard` to visualize the metrics related to LLM invocations and costs. Additionally, it sets up an SNS topic (`BedrockInvocationAlarms`) to receive email alerts based on configurable thresholds for cost, token usage, and request counts.

## Customization

You can easily extend or modify the project to suit your specific needs. For example, you could add support for additional LLM providers, customize the dashboard layout, or integrate with other monitoring and alerting systems.

## Contributing

Contributions to this project are welcome. If you encounter any issues or have ideas for improvements, please open an issue or submit a pull request.
