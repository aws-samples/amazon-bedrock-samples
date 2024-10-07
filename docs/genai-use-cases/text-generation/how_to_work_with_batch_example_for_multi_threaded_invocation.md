---
tags:
    - Use cases
    - API-Usage-Example
---
<!-- <h2> Batch Inference to write email for product recomendation</h2> -->
!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main//genai-use-cases/text-generation/how_to_work_with_text_generation_w_bedrock.ipynb){:target="_blank"}"

<h2>Overview</h2>

In the world of e-commerce and digital marketing, personalized product recommendations are crucial for engaging customers and driving sales. However, creating individualized marketing emails for thousands of customers can be time-consuming and resource-intensive. This notebook presents a solution using Amazon Bedrock's batch inference capabilities to automate and scale this process.


<h2>Context</h2>

This Jupyter notebook demonstrates how to use Amazon Bedrock for batch inference to generate personalized product recommendation emails at scale. It showcases a multi-threaded invocation job pattern, allowing for efficient processing of large datasets.


<h3>Use case</h3>

An e-commerce company wants to send personalized product recommendation emails to its large customer base. The marketing team needs to:
- Generate customized email content for each customer based on their name and a recommended product.
- Process thousands of customer records efficiently.
- Create engaging, human-like email copy that feels personalized to each recipient.
- Scale the email generation process to handle growing customer lists without increasing manual effort.

This solution addresses these needs by leveraging Amazon Bedrock's language models to generate personalized email content in a batch process, allowing the marketing team to create thousands of customized emails quickly and efficiently.


<h3>Pattern</h3>

The pattern used in this notebook is a Batch Inference with Multi-threaded Invocation Job. This approach allows for:
- Generation of synthetic customer and product data
- Preparation of input data for the language model
- Batch processing of multiple inputs in parallel
- Efficient use of compute resources
- Scalable generation of personalized marketing emails


<h3>Persona</h3>

This solution is designed for:
- Marketing teams in e-commerce companies
- Data scientists and ML engineers working on customer personalization
- Product managers looking to implement scalable recommendation systems


<h3>Implementation</h3>
The implementation consists of the following key components:
- Data Generation: Creation of synthetic customer names and product recommendations
- Input Preparation: Formatting the data for the language model
- S3 Integration: Uploading input data to Amazon S3
- Batch Job Configuration: Setting up the Amazon Bedrock batch inference job
- Job Execution and Monitoring: Running the batch job and checking its status

<h2>Prerequisites</h2>

Before you can use Amazon Bedrock, you must carry out the following steps:

- Sign up for an AWS account (if you don't already have one) and IAM Role with the necessary permissions for Amazon Bedrock, see [AWS Account and IAM Role](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#new-to-aws){:target="_blank"}.
- Request access to the foundation models (FM) that you want to use, see [Request access to FMs](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#getting-started-model-access){:target="_blank"}. 

<h2>Setup</h2>

```python
import random
import string
import json
import boto3
import sagemaker
import os

sess = sagemaker.Session()
bucket = sess.default_bucket()
role = sagemaker.get_execution_role()

bedrock = boto3.client(service_name="bedrock")
```

<h2>Prepare synthetic dataset</h2>


```python
# Define lists for generating synthetic product data

adjectives = ["Cutting-edge", "Innovative", "Premium", "Advanced", "Powerful", "Sleek", "Stylish"]
nouns = ["Smartwatch", "Headphones", "Laptop", "Tablet", "Smartphone", "Speaker", "Camera"]
descriptions = [
    "Designed to help you stay motivated and achieve your fitness goals.",
    "Featuring advanced noise-canceling technology and long-lasting battery life.",
    "With its lightweight and portable design, perfect for on-the-go productivity.",
    "Offering an immersive entertainment experience with stunning visuals and powerful sound.",
    "Capture every moment with stunning clarity and detail.",
    "Seamlessly blending fashion and functionality.",
    "Unleash your creativity with powerful performance and cutting-edge features."
]

# Function to generate synthetic customer names and product recommendations
def generate_data(num_names):
    names = []
    product_recs = []

    for _ in range(num_names):
        first_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
        last_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
        name = f"{first_name} {last_name}"
        names.append(name)

        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        desc = random.choice(descriptions)
        product_name = f"{adj} {noun}"
        product_description = f"{product_name} {desc}"

        product_rec = {
            "product_name": product_name,
            "product_description": product_description
        }
        product_recs.append(product_rec)

    return names, product_recs


```


```python
# Generate data
num_names = 12000
names, product_recs = generate_data(num_names)


```


```python
# Function to generate model input data for batch inference
def generate_model_input(names, product_recs):
    model_inputs = []

    for i, name in enumerate(names):
        record_id = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        product_rec = product_recs[i % len(product_recs)]

        input_text = f"Write a marketing email for the customer based on the provided product and description: Customer Name: {name} | Recommended Product(s): {product_rec['product_name']} | Product Description: {product_rec['product_description']}"        

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": 'user',
                     "content": [
                         {'type': 'text',
                          'text': input_text}]
                     }],
            "max_tokens": 300,
            "temperature": 0.9,
            "top_p": 0.9,
            "top_k": 100,
        } 

        model_input = {
            "recordId": record_id,
            "modelInput": body
        }
        
        model_inputs.append(model_input)

    return model_inputs

# Function to write data to a JSONL file
def write_jsonl(data, file_path):
    with open(file_path, 'w') as file:
        for item in data:
            json_str = json.dumps(item)
            file.write(json_str + '\n')

# Function to upload files or directories to an S3 bucket
def upload_to_s3(path, bucket_name, bucket_subfolder=None):
    """
    Upload a file or directory to an AWS S3 bucket.

    :param path: Path to the file or directory to be uploaded
    :param bucket_name: Name of the S3 bucket
    :param bucket_subfolder: Name of the subfolder within the S3 bucket (optional)
    :return: True if the file(s) were uploaded successfully, False otherwise
    """
    s3 = boto3.client('s3')

    if os.path.isfile(path):
        # If the path is a file, upload it directly
        object_name = os.path.basename(path) if bucket_subfolder is None else f"{bucket_subfolder}/{os.path.basename(path)}"
        try:
            s3.upload_file(path, bucket_name, object_name)
            print(f"Successfully uploaded {path} to {bucket_name}/{object_name}")
            return True
        except Exception as e:
            print(f"Error uploading {path} to S3: {e}")
            return False
    elif os.path.isdir(path):
        # If the path is a directory, recursively upload all files within it
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                object_name = relative_path if bucket_subfolder is None else f"{bucket_subfolder}/{relative_path}"
                try:
                    s3.upload_file(file_path, bucket_name, object_name)
                    print(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
                except Exception as e:
                    print(f"Error uploading {file_path} to S3: {e}")
        return True
    else:
        print(f"{path} is not a file or directory.")
        return False
```


```python
# Generate model inputs
model_inputs = generate_model_input(names, product_recs)

# Write model inputs to a jsonl file
write_jsonl(model_inputs, 'model_inputs.jsonl')
```


```python
# Upload the generated JSONL file to an S3 bucket
upload_to_s3("model_inputs.jsonl", 
             bucket, 
             bucket_subfolder='batch-inf-test')
```


<h2>Setup Batch Inference Job:</h2>


```python
# Configure input and output data configurations for the batch job
inputDataConfig=({
    "s3InputDataConfig": {
        "s3Uri": f"s3://{bucket}/batch-inf-test/model_inputs.jsonl"
    }
})

outputDataConfig=({
    "s3OutputDataConfig": {
        "s3Uri": f"s3://{bucket}/batch-inf-test/out/"
    }
})


```


```python
# Create a model invocation job for batch inference
response=bedrock.create_model_invocation_job(
    roleArn=role,
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    jobName="batch-job-v11",
    inputDataConfig=inputDataConfig,
    outputDataConfig=outputDataConfig
)

jobArn = response.get('jobArn')
```


```python
# Check the status of the batch inference job
bedrock.get_model_invocation_job(jobIdentifier=jobArn)['status']
```

<h2>Next Steps</h2>

The multi-threaded invocation job pattern demonstrated in this example allows for efficient processing of large datasets, making it an excellent solution for generating personalized marketing content at scale. By leveraging Amazon Bedrock's batch inference capabilities, marketing teams can automate the creation of customized product recommendation emails, saving time and resources while potentially improving customer engagement and sales.

- Adapt this notebook to experiment with different models available through Amazon Bedrock 
- Apply different prompt engineering principles to get better outputs. Refer to the prompt guide for your chosen model for recommendations, e.g. [here is the prompt guide for Claude](https://docs.anthropic.com/claude/docs/introduction-to-prompt-design).


<h2>Cleanup</h2>

There is no clean up necessary for this notebook.
