# Amazon Bedrock Inference Cost Monitoring & Allocation

## 📌 Overview

This project provides a structured approach to monitor and allocate inference costs for applications utilizing Amazon Bedrock. By leveraging Application Inference Profiles (AIPs), AWS tagging, and CloudWatch dashboards, it enables detailed cost tracking across various dimensions such as applications, tenants, and environments.

## 🧰 Features

- **Application Inference Profiles (AIPs)**: Create AIPs for each combination of application, tenant, and environment to isolate and monitor usage.
- **AWS Tagging Integration**: Utilize AWS tags to associate metadata with each AIP, facilitating granular cost allocation.
- **Automated Setup**: Deploy necessary AWS resources including Lambda functions, API Gateway endpoints, CloudWatch dashboards, and SNS alerts using a setup script.
- **Real-Time Monitoring**: Visualize inference usage and costs through a Streamlit dashboard integrated with CloudWatch metrics.

## ⚙️ Prerequisites

Before setting up the project, ensure the following:
- **AWS Account**: An active AWS account with permissions to create and manage resources such as Lambda functions, API Gateway, CloudWatch, and SNS.
- **Python Environment**: Python 3.12 or higher installed on your local machine.
- **Virtual Environment Setup**: It's recommended to use a virtual environment to manage project dependencies.

## 📝 Configuration

Prior to executing the setup script, update the configuration files to reflect your specific use case.

1. **Update config/config.json**: Define your applications, profiles, environments, and associated tags.
   
   Example structure:

```json
{
  "profiles": [
    {
      "name": "CustomerOneWebSearchBot", 
      "description": "For Customer-1 using Websearch Bot",
      "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
      "tags": [
                {
                    "key": "CreatedBy",
                    "value": "Dev-Account"
                },
                {
                    "key": "ApplicationID",
                    "value": "Web-Search-Bot"
                },
                {
                    "key": "Environment",
                    "value": "Dev"
                }
         ...
      ]
    },
    {
      "name": "CustomerOneCodeAssistant",
      "description": "For Customer-1 using Coding Assistant Bot",
      "model_id": "amazon.nova-pro-v1:0",
      "tags": [
                {
                    "key": "CreatedBy",
                    "value": "Prod-Account"
                },
                {
                    "key": "ApplicationID",
                    "value": "Coding-Assistant-Bot"
                },
                {
                    "key": "Environment",
                    "value": "Prod"
                }
         ...
      ]
    }
  ]
}
```

2. **Update config/models.json**: Specify the pricing details for each model, including input and output token costs.
   
   Example structure:

```json
{
  "anthropic.claude-3-haiku-20240307-v1:0": {
    "input_cost": 0.00163,
    "output_cost": 0.00551
  },
  "amazon.nova-pro-v1:0": {
    "input_cost": 0.00075,
    "output_cost": 0.001
  }
}
```

## 🚀 Setup Instructions

Follow these steps to set up the project:

1. **Clone the Repository**:

```bash
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
cd amazon-bedrock-samples/poc-to-prod/inference-profiles/inference-profile-cost-tracing
```

2. **Set Up Virtual Environment**:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use 'venv\Scripts\activate'
```

3. **Install Dependencies**:

```bash
pip install -r requirements.txt
```

4. **Execute Setup Script including User Roles**:

```bash
python setup.py --create-user-roles
```
5. **Execute Setup Script excluding User Roles**:

```bash
python setup.py
```

This script will:
- Create Application Inference Profiles based on your configuration.
- Deploy Lambda functions responsible for capturing metadate.
- Deploy API Gateway endpoints (you will use this to run your inferences).
- Set up CloudWatch dashboards and SNS alerts for monitoring.


**Clean all created Assets**:

```bash
python unsetup.py
```

## 📊 CloudWatch Dashboard
An example of the CloudWatch dashboard displaying inference usage and cost metrics.

<img src="assets/gif-dashboard.png" width="70%" height="70%"/>


## 🎥 Video Tutorial

For a comprehensive walkthrough of the solution, watch the following video:

[![Video Tutorial](https://img.youtube.com/vi/OTbVOuAmsZk/0.jpg)](https://www.youtube.com/watch?v=OTbVOuAmsZk&t=686s)

----
## 🧾 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.