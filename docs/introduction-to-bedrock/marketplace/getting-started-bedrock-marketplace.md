# Getting Started with Amazon Bedrock Marketplace

----

### 1. Introduction

Amazon Bedrock Marketplace enables access to hundreds of proprietary and publicly available foundation models through a self-hosted approach. Unlike the serverless Bedrock models, Bedrock Marketplace models provide:

- **Self-deployed endpoints**: You control capacity, throughput, and operational parameters through endpoint configurations.
- **Integration with Bedrock tools**: Many models are compatible with Converse API, Model Evaluation, Guardrails, and other Bedrock features.
- **SageMaker compatibility**: Being effectively a way to expose SageMaker Jumpstart endpoints, it allows further customizing your Bedrock Marketplace endpoints in SageMaker, or even registering existing SageMaker endpoints.

**Key Differences vs SageMaker JumpStart**

While both services provide easy-to-deploy foundation model capabilities:
- Bedrock Marketplace focuses on the built-in integration with Bedrock's features and ecosystem.
- SageMaker JumpStart provides more customization and integration with the SageMaker ecosystem.

For more information on Bedrock Marketplace, visit the documentation [here]().

#### Example Use Cases

In this notebook, we'll explore some example use cases for illustrating the use of Bedrock Marketplace.

1. **Domain Specific Q&A**: Using domain-specific models for improving the performance of responses, e.g.: using the "Medical LLM" model for answering deep and specific medical questions.
2. **Language Translation**: Deploying task-specific models for improving the performance of responses, e.g.: using "EXAONE" for a Japanese-English translation.
3. **Custom Model Integration**: Bringing existing SageMaker Jumpstart endpoints to Bedrock Marketplace, for leveraging Bedrock's Converse API.


----


### 2. Setup

First, let's install required dependencies and configure our environment.


```python
# Make sure you have the latest boto3 and sagemaker versions...
!pip3 install boto3 sagemaker --upgrade --quiet
```


```python
import boto3, sagemaker
import json

print(f'Boto3 version: {boto3.__version__}')
region = 'us-west-2'  # Change with your preferred region as needed
print(f'Using region: {region}')

session = boto3.Session(region_name=region, profile_name='default') # Change with your preferred profile as needed
bedrock_client = session.client('bedrock', region_name=region)
sagemaker_client = session.client('sagemaker', region_name=region)
bedrock_runtime = session.client('bedrock-runtime', region_name=region)
sts_client = session.client('sts', region_name=region)
account_id = sts_client.get_caller_identity()["Account"]
print(f'Account ID: {account_id}')

```

#### Pre-requisites

For this example we'll need two AWS IAM execution roles:
* One with permissions for creating and managing the Marketplace endpoints in Amazon Bedrock
* Another with permissions for creating Jumpstart endpoints in Amazon SageMaker

For this, you can either create the roles with the code below, or alternatively if you already have roles configured for this comment this out and provide the ARNs of your own roles for the execution_role variables at the end.


```python
# Execution roles
def create_sagemaker_role(sagemaker_role_name):
    iam_client = session.client('iam')

    # Trust policy for AWS services
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "sagemaker.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    # SageMaker endpoint management policy
    with open('sagemaker_policy.json', 'r') as file:
        sagemaker_policy = json.load(file)
    
    try:
        # Create SageMaker role
        sagemaker_role = iam_client.create_role(
            RoleName=sagemaker_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        # Create and attach SageMaker policy
        sagemaker_policy_name = f"{sagemaker_role_name}Policy"
        iam_client.create_policy(
            PolicyName=sagemaker_policy_name,
            PolicyDocument=json.dumps(sagemaker_policy)
        )
        iam_client.attach_role_policy(
            RoleName=sagemaker_role_name,
            PolicyArn=f"arn:aws:iam::{sts_client.get_caller_identity()['Account']}:policy/{sagemaker_policy_name}"
        )
        print(f"Created SageMaker execution role: {sagemaker_role['Role']['Arn']}")
        return sagemaker_role['Role']['Arn']
        
    except Exception as e:
        print(f"Error creating SageMaker execution role: {str(e)}")
        raise

def create_bedrock_role(bedrock_role_name):
    iam_client = session.client('iam')
    
    # Trust policy for AWS services
    trust_policy = {
    	"Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "bedrock.amazonaws.com",
                        "sagemaker.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Bedrock access policy
    with open('bedrock_policy.json', 'r') as file:
        bedrock_policy = json.load(file)
    
    try:
        # Create Bedrock role
        bedrock_role = iam_client.create_role(
            RoleName=bedrock_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        # Create and attach Bedrock policy
        bedrock_policy_name = f"{bedrock_role_name}Policy"
        iam_client.create_policy(
            PolicyName=bedrock_policy_name,
            PolicyDocument=json.dumps(bedrock_policy)
        )
        iam_client.attach_role_policy(
            RoleName=bedrock_role_name,
            PolicyArn=f"arn:aws:iam::{sts_client.get_caller_identity()['Account']}:policy/{bedrock_policy_name}"
        )
        print(f"Created Bedrock execution role: {bedrock_role['Role']['Arn']}")
        return bedrock_role['Role']['Arn']
        
    except Exception as e:
        print(f"Error creating Bedrock Marketplace execution role: {str(e)}")
        raise

# Run this if you want to create new roles...
sagemaker_execution_role = create_sagemaker_role('SageMakerJumpstartRole')
bedrock_execution_role = create_bedrock_role('BedrockMarketplaceRole')

# Or, uncomment and set this if you already have your own roles...
#sagemaker_execution_role = 'YOUR-SAGEMAKER-ROLE-ARN'
#bedrock_execution_role = 'YOUR-BEDROCK-ROLE-ARN'

```

----

### 3. Exploring Available Models

#### Bedrock Console Exploration

To discover an Amazon Bedrock Marketplace model:
* Access your Amazon Bedrock Console
* Select **Model Catalog** from the left navigation pane.
* For **Model Collection** check the **Bedrock Marketplace** option, to load Amazon Bedrock Marketplace models.
* You can further filter and open any of the models for reading its model card

For more information read the [Bedrock Marketplace](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-marketplace-discover-a-model.html) documentation.

#### Programmatic Exploration

You can also programmatically explore the available models using the SageMaker Jumpstart APIs, filtering for Bedrock Marketplace models as follows.


```python
def list_bedrock_marketplace_models(SM_HUB_NAME='SageMakerPublicHub', SM_HUB_CONTENT_TYPE='Model'):
    from sagemaker.jumpstart.notebook_utils import list_jumpstart_models
    
    # List foundation models in the SageMaker Jumpstart public hub...
    jumpstart_models = sagemaker_client.list_hub_contents(
                MaxResults=150,
                HubName=SM_HUB_NAME,
                HubContentType=SM_HUB_CONTENT_TYPE
            )

    # Filter out the models with Bedrock capability...
    bedrock_models = []
    for model in sorted(
        [model for model in jumpstart_models['HubContentSummaries'] 
        if 'HubContentSearchKeywords' in model and '@capability:bedrock_console' in model['HubContentSearchKeywords']],
        key=lambda x: x['HubContentDisplayName']):
        bedrock_models.append(model)
    
    return bedrock_models

print(f'Bedrock Marketplace Models:\n')
for i, model in enumerate(list_bedrock_marketplace_models(), 1):
    print(f"{i}. {model['HubContentDisplayName']} - ({model['HubContentArn']})")
```

You can further explore the details of any of the models...


```python
def describe_model(model_name, SM_HUB_NAME='SageMakerPublicHub'):
    model = sagemaker_client.describe_hub_content(
                HubName=SM_HUB_NAME,
                HubContentType='Model',
                HubContentName=model_name
            )
    print(json.dumps(model, indent=4, default=str))
    return

describe_model('ibm-granite-34b-code-instruct-8k')
```

----

### 4. Deploying Models

Now let's deploy our models using the Bedrock Marketplace APIs.

For our example use cases we'll choose:
* **Medical LLM - Small** from **John Snow Labs**, as our domain-specific medical Q&A
* **EXAONE_v3.0 7.8B Instruct** from **LG CNS**, as our task-specific Japanese-English translator

**Note**: For proprietary models you must first subscribe in the Amazon Bedrock Marketplace console, in order to get access to them.
For the models in our example you can do this with the following links (adjust the region as required):
* Medical LLM Small - https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/model-catalog/bedrock-marketplace/john-snow-labs-summarization-qa
* Exaone 7.8 Instruct - https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/model-catalog/bedrock-marketplace/exaone-v3-0-7-8b-instruct

Read the details and click on **View Subscription Options**, then click **Subscribe**

#### Deploy Endpoints

Once subscribed, you're ready to deploy your first Bedrock Marketplace endpoints for these models.


```python
import json
import json
def create_marketplace_endpoint(model_arn, endpoint_name, instance_type, execution_role):
    # Create a Bedrock Marketplace endpoint...
    try:
        response = bedrock_client.create_marketplace_model_endpoint(
            modelSourceIdentifier=model_arn,
            endpointName=endpoint_name,
            acceptEula=True,
            endpointConfig={
                'sageMaker': {
                    'initialInstanceCount': 1,
                    'instanceType': instance_type,
                    'executionRole': execution_role
                }
            }
        )
        #print(json.dumps(response, indent=2, default=str))
        return response['marketplaceModelEndpoint']['endpointArn']
    except Exception as e:
        print(e)
        return

# Choosing models... Replace the ARN here for the desired model of your choice from the list provided before.
MODEL_ARN_MEDICAL = 'arn:aws:sagemaker:us-west-2:aws:hub-content/SageMakerPublicHub/Model/john-snow-labs-summarization-qa/1.1.2'
MODEL_ARN_TRANSLATION = 'arn:aws:sagemaker:us-west-2:aws:hub-content/SageMakerPublicHub/Model/exaone-v3-0-7-8b-instruct/1.0.0'

# Deploy medical model...
medical_endpoint_arn = create_marketplace_endpoint(
    model_arn=MODEL_ARN_MEDICAL,
    endpoint_name='medical-summarizer',
    instance_type='ml.g5.2xlarge',
    execution_role=bedrock_execution_role
)
print(f'Deploying Bedrock Markeplace Endpoint with ARN: "{medical_endpoint_arn}"')

# Deploy translation model...
translation_endpoint_arn = create_marketplace_endpoint(
    model_arn=MODEL_ARN_TRANSLATION,
    endpoint_name='jp-en-translator',
    instance_type='ml.g5.4xlarge',
    execution_role=bedrock_execution_role
)
print(f'Deploying Bedrock Markeplace Endpoint with ARN: "{translation_endpoint_arn}"')

```


```python
# Alternatively, if you already have your endpoints deployed, uncomment and provide your Bedrock Marketplace endpoint ARNs here...
#medical_endpoint_arn = 'arn:aws:sagemaker:us-west-2:XXXXXXXXXXXX:endpoint/medical-summarizer'
#translation_endpoint_arn = 'arn:aws:sagemaker:us-west-2:XXXXXXXXXXXX:endpoint/jp-en-translator'
```


```python
def wait_for_bedrock_endpoint(endpoint_arn):
    # Wait for endpoint to be ready...
    import time
    from datetime import datetime
    while True:
        response = bedrock_client.get_marketplace_model_endpoint(
            endpointArn=endpoint_arn
        )
        name = response['marketplaceModelEndpoint']['endpointArn'].split('/')[-1]
        status = response['marketplaceModelEndpoint']['endpointStatus']
        print(f'{datetime.now().strftime('%H:%M:%S')} Endpoint {name} - Status: {status}')
        if status == 'InService':
            break
        time.sleep(30)

# Wait for endpoints to be ready...
wait_for_bedrock_endpoint(medical_endpoint_arn)
wait_for_bedrock_endpoint(translation_endpoint_arn)
```

#### Test Endpoints
Let's test our deployed endpoints using the Bedrock Runtime client.

Note, some models support the unified Bedrock [Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) API, while others require the use of the [InvokeModel](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html) API.

You can check the compatibility list in the [Bedrock Marketplace](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-marketplace-model-reference.html) documentation.

In all cases, you can also test your deployed models from the Bedrock Console by using the provided Playgrounds.


```python
# Test the medical model with Bedrock's InvokeModel API...

def invoke_marketplace_endpoint(id, user_prompt, max_tokens=1024, temperature=0.1):
    import json, traceback
    try:
        response = bedrock_runtime.invoke_model(
            modelId=id,
            body=json.dumps({
                "input_text": user_prompt,
                "max_new_tokens": max_tokens,
                "temperature": temperature
            })
        )
        # Extract and show the response text...
        output = json.loads(response["body"].read())
        print(output['response'][0])
        return
    except Exception as e:
        print(traceback.format_exc())
        return f"Error: {str(e)}"

# Adjust the user prompt according to your own use case requirements...
medical_user_prompt = """In a patient presenting with digital clubbing, polycythemia, and platypnea-orthodeoxia syndrome,
what congenital cardiovascular anomaly would be highest on your differential diagnosis,
and what specific embryological defect underlies its development?
"""

invoke_marketplace_endpoint(medical_endpoint_arn, medical_user_prompt)
```


```python
# Test the translation model with Bedrock's ConverseStream API...

def converse_marketplace_endpoint(id, user_prompt, system_prompt, max_tokens=2000, temperature=0):
    import sys, traceback
    response = ''
    try:
        response = bedrock_runtime.converse(
            modelId=id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": user_prompt
                        }
                    ]
                }
            ],
            system=[ # Optional, remove this parameter if preferred
                { "text": system_prompt }
            ],
            inferenceConfig={ # Adjust/remove parameters as needed
                "temperature": temperature,
                "maxTokens": max_tokens,
                #"topP": top_p
            }
            #additionalModelRequestFields={ # Adjust/remove parameters as needed
            #}
        )
        # Extract and show the response text...
        print(response['output']['message']['content'][0]['text'])
        return
    except Exception as e:
        print(traceback.format_exc())
        return f"Error: {str(e)}"

# Adjust the user prompt according to your own use case requirements...
translation_user_prompt = """
Translate the following text from Japanese to English:
生成 AI プランニングまたは生成プランニングという用語は、1980 年代から 1990 年代にかけて、特定の目標を達成するための一連のアクションを生成するために使用される AI プランニング システム、特にコンピューター支援プロセス プランニングを指すために使用されていました。
"""

# System prompt is optional, remove if preferred for your use case...
translation_system_prompt = """
You are a translation expert assistant for the company Octank.
"""

converse_marketplace_endpoint(translation_endpoint_arn, translation_user_prompt, translation_system_prompt)
```

#### List Endpoints

We can also list all the Bedrock Marketplace endpoints in our account...


```python
# List all endpoints
response = bedrock_client.list_marketplace_model_endpoints()
print('Current endpoints:')
for endpoint in response['marketplaceModelEndpoints']:
    print(json.dumps(endpoint, indent=2, default=str))
```

-----

#### Update Endpoints - Basic configurations

You can also update the configurations of the endpoint already deployed with Bedrock Marketplace.

In example, we could change the number of instances or instance type with the code below...


```python
# Update endpoint configuration
try:
    response = bedrock_client.update_marketplace_model_endpoint(
        endpointArn=medical_endpoint_arn,
        endpointConfig={
            'sageMaker': {
                'initialInstanceCount': 2,  # Scaling up to handle more traffic
                'instanceType': 'ml.g5.2xlarge',
                'executionRole': bedrock_execution_role
            }
        }
    )
    print(json.dumps(response, indent=4, default=str))
except Exception as e:
    print(e)
```

#### Update Endpoints - Advanced configurations

We can also rely on the SageMaker SDK or the SageMaker Console to perform useful tasks with our Bedrock Marketplace endpoints.

In example, we can setup an Auto-Scaling policy for ensure it dynamically adds or removes instances as the demand to our model changes. For doing this, you can follow the code above, or follow the steps in the [SageMaker documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling-add-console.html).


```python
#Let us define a client to play with autoscaling options
endpoint_name = 'medical-summarizer' ### Replace with your endpoint name
endpoint_variant = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)['ProductionVariants'][0]['VariantName']
resource_id = f'endpoint/{endpoint_name}/variant/{endpoint_variant}'
print(f'Resource ID: {resource_id}')

# Register a scalable target for our Bedrock Marketplace endpoint 'medical-summarizer', with a min capacity of 1 instance and max capacity of 2 instances
try:
    import traceback
    autoscaling_client = session.client('application-autoscaling', region_name=region)
    response = autoscaling_client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId=resource_id,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=1,
        MaxCapacity=2
    )
    print(json.dumps(response, indent=4, default=str))
except Exception as e:
    print(traceback.format_exc())
    print(e)
```


```python
#Example 1 - SageMakerVariantInvocationsPerInstance Metric
response = autoscaling_client.put_scaling_policy(
    PolicyName='Invocations-ScalingPolicy',
    ServiceNamespace='sagemaker',
    ResourceId=resource_id, # Endpoint name 
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling', # 'StepScaling'|'TargetTrackingScaling'
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 10.0, # The target value for the metric: SageMakerVariantInvocationsPerInstance
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance', # average number of times per minute that each instance for a variant is invoked. 
        },
        'ScaleInCooldown': 600, # The cooldown period helps you prevent your Auto Scaling group from launching or terminating 
                                # additional instances before the effects of previous activities are visible. 
                                # You can configure the length of time based on your instance startup time or other application needs.
                                # ScaleInCooldown - The amount of time, in seconds, after a scale in activity completes before another scale in activity can start. 
        'ScaleOutCooldown': 300 # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another scale out activity can start.
        # 'DisableScaleIn': True|False - ndicates whether scale in by the target tracking policy is disabled. 
                            # If the value is true , scale in is disabled and the target tracking policy won't remove capacity from the scalable resource.
    }
)

#Example 2 - CPUUtilization metric
response = autoscaling_client.put_scaling_policy(
    PolicyName='CPUUtil-ScalingPolicy',
    ServiceNamespace='sagemaker',
    ResourceId=resource_id,
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 90.0,
        'CustomizedMetricSpecification':
        {
            'MetricName': 'CPUUtilization',
            'Namespace': '/aws/sagemaker/Endpoints',
            'Dimensions': [
                {'Name': 'EndpointName', 'Value': 'endpoint_name' },
                {'Name': 'VariantName','Value': 'AllTraffic'}
            ],
            'Statistic': 'Average', # Possible - 'Statistic': 'Average'|'Minimum'|'Maximum'|'SampleCount'|'Sum'
            'Unit': 'Percent'
        },
        'ScaleInCooldown': 600,
        'ScaleOutCooldown': 300
    }
)
```

For more details on setting-up auto-scaling policies you can refer to the AWS ML blog: [Configuring autoscaling inference endpoints in Amazon SageMaker](https://aws.amazon.com/blogs/machine-learning/configuring-autoscaling-inference-endpoints-in-amazon-sagemaker/).

Note there are other customizations that you might want to consider for your endpoints, such as having autoscaling policies, or adjusting other details of the configuration. For these tasks you can still rely on the Amazon SageMaker features, as your endpoints will show up as regular SageMaker Endpoints.

For more information on how to use Amazon SageMaker for Endpoints customization you can check the documentation [here](TBC).

----

### 5. Custom Model Integration

The final use case that we'll explore in this notebook is the situation where you already have an existing SageMaker Endpoint with a Jumpstart foundation model, and you want to register it in Bedrock Marketplace for using with the Bedrock features.

For illustrating this, we'll start by deploying an endpoint with a foundation model from SageMaker Jumpstart.

Alternatively, if you already have a deployed SageMaker endpoint for a compatible Jumpstart model, you can skip this cell and go directly to the registration in Bedrock Marketplace. In this case make sure you adjust the variable `sagemaker_endpoint` to your endpoint name.

Note the SageMaker Endpoint deployment can take 5-7 mins...


```python
# Deploy a model using SageMaker JumpStart...
from sagemaker.jumpstart.model import JumpStartModel
print(f'Using role: {sagemaker_execution_role}')

sagemaker_session = sagemaker.Session(boto_session=session)
sagemaker_model_id = 'huggingface-text2text-flan-t5-base' # Replace with any Jumpstart model of your choice from the supported list provided before
sagemaker_model_version = '2.2.3' # Replace with the version of the model you want to deploy
my_model = JumpStartModel(
    model_id=sagemaker_model_id,
    model_version=sagemaker_model_version,
    role=sagemaker_execution_role,
    region=region,
    sagemaker_session=sagemaker_session,
    enable_network_isolation=True
)
predictor = my_model.deploy()

sagemaker_endpoint = predictor.endpoint_name
print(f'SageMaker Endpoint name: {sagemaker_endpoint}')
```


```python
response = sagemaker_client.describe_endpoint(EndpointName=sagemaker_endpoint)
sagemaker_endpoint_arn = response['EndpointArn']
print(f'SageMaker Endpoint ARN: {sagemaker_endpoint_arn}')
```

#### Register Endpoint in Bedrock Marketplace

We can now register our endpoint with the Bedrock Marketplace...


```python
# Register the SageMaker endpoint with Bedrock
source_identifier = f'arn:aws:sagemaker:{region}:aws:hub-content/SageMakerPublicHub/Model/{sagemaker_model_id}/{sagemaker_model_version}'
try:
    response = bedrock_client.register_marketplace_model_endpoint(
        endpointIdentifier=sagemaker_endpoint_arn,
        modelSourceIdentifier=source_identifier
    )
    registered_endpoint = response['marketplaceModelEndpoint']
    registered_endpoint_arn = registered_endpoint['endpointArn']
    print(f'Registered endpoint: {json.dumps(registered_endpoint, indent=2, default=str)}')
except Exception as e:
    print(e)
```

Finally, let's test our registered endpoint with the Bedrock's Converse API...


```python
user_prompt = """What is cloud computing? answer with a single sentence"""
system_prompt = """You're a helpful virtual assistant"""

converse_marketplace_endpoint(registered_endpoint_arn, user_prompt, system_prompt)
```

----

### 6. Cleanup

You've reached to the end of this example.


Once done testing, remember to clean-up any un-used endpoints to avoid unnecessary charges.


```python
# Delete Bedrock Marketplace endpoints...
#medical_endpoint_arn = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
#translation_endpoint_arn = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
#registered_endpoint_arn = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
for endpoint_arn in [medical_endpoint_arn, translation_endpoint_arn, registered_endpoint_arn]:
    try:
        bedrock_client.delete_marketplace_model_endpoint(
            endpointArn=endpoint_arn
        )
        print(f'Deleted endpoint: {endpoint_arn}')
    except:
        pass

# Delete SageMaker endpoint...
try:
    predictor.delete_endpoint()
    print(f'Deleted endpoint: {sagemaker_endpoint_arn}')
except:
    pass
```

#### Deregister Endpoint (optional)

In some specific cases, you might want to Deregister and endpoint from the Bedrock Marketplace.

Note this action will NOT delete the endpoints themselves but only delete any metadata about this endpoint stored in Bedrock Marketplace, effectively making it unusable in Bedrock. This could be useful for some specific cases like e.g. for compliance or regulatory reasons.


```python
#try:
#    response = bedrock_client.deregister_marketplace_model_endpoint(
#        endpointArn=registered_endpoint_arn # Replace with your endpoint ARN
#    )
#    print(f'Deregistered endpoint with ARN: {endpoint_arn}')
#except Exception as e:
#        print(e)
```
