import argparse  # noqa: INP001
import logging
import random
import time
import uuid
from datetime import datetime
from functools import wraps

import boto3
from botocore.exceptions import ClientError

# Configure logging for notebook environment
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def retry_with_exponential_backoff(max_retries=3, base_delay=2):
    """Decorator for retrying functions with exponential backoff when throttled."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:  # noqa: PERF203
                    if e.response["Error"]["Code"] == "ThrottlingException":
                        if attempt == max_retries - 1:
                            logger.exception(f"Function {func.__name__} failed after {max_retries} attempts. Error: {e!s}")  # noqa: G004, TRY401
                            raise
                        wait_time = (base_delay * (2 ** attempt)) + (random.random() * 0.1)
                        logger.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time:.2f} seconds...")  # noqa: G004
                        time.sleep(wait_time)
                    else:
                        logger.exception(f"Client error: {e!s}")  # noqa: G004, TRY401
                        raise
                except Exception as e:
                    logger.exception(f"Unexpected error in {func.__name__}: {e!s}")  # noqa: G004, TRY401
                    raise
            return wrapper
        return wrapper
    return decorator


@retry_with_exponential_backoff(max_retries=3, base_delay=2)
def generate_conversation(client, model_id, system_prompt, prompt, metadata=None):
    """
    Sends messages to a model using the Bedrock Runtime converse API.

    Args:
        client: Bedrock runtime client
        model_id: The ID of the model to use
        system_prompt: The system prompt to guide the model behavior
        prompt: The user prompt to send to the model
        metadata: Dictionary containing metadata for analytics (e.g., tenantId, department, costCenter)

    Returns:
        The model's response

    """
    # Construct the messages array
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        },
    ]

    # Construct the system message
    system = [{"text": system_prompt}]

    # Inference parameters
    inference_config = {
        "temperature": 0.1,
        "topP": 0.95,
        "maxTokens": 500,  # Reduced for faster responses
    }

    # Default empty metadata if none provided
    if metadata is None:
        metadata = {}

    try:
        # Include requestMetadata in the API call
        response = client.converse(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
            requestMetadata=metadata,
        )

        # Extract the generated message from the response
        output = response["output"]["message"]
        return output  # noqa: TRY300
    except client.exceptions.ValidationException as e:
        logger.exception(f"Validation error: {e!s}")  # noqa: G004, TRY401
        raise
    except Exception as e:
        logger.exception(f"An error occurred: {e!s}")  # noqa: G004, TRY401
        raise

# Sample data for generating diverse metadata
companies = [
    "Acme Corporation", "TechNova", "DataSphere", "CloudPeak",
    "Quantum Solutions", "Alpine Industries", "Horizon Healthcare",
]

departments = [
    "Marketing", "Sales", "Engineering", "Finance", "HR",
    "Customer Support", "Product", "Research", "Legal", "Operations",
]

# Sample tenants with consistent identifiers
tenants = [
    "tenant-alpha", "tenant-beta", "tenant-gamma", "tenant-delta", "tenant-epsilon",
]

cost_centers = ["CC-1001", "CC-1002", "CC-2001", "CC-3001", "CC-4001"]

use_cases = [
    "customer-service", "product-description", "content-creation",
    "data-analysis", "report-generation", "policy-review",
    "email-drafting", "knowledge-base", "translation",
]

environments = ["dev", "test", "staging", "production"]

# Sample prompts for different contexts
prompts = [
    "Summarize the key benefits of cloud computing for small businesses.",
    "What are the latest trends in artificial intelligence?",
    "Explain machine learning in simple terms.",
    "How can data analytics improve business decision making?",
    "What are the best practices for cybersecurity in 2024?",
    "Compare SQL and NoSQL databases for enterprise applications.",
    "What is the importance of digital transformation for businesses?",
    "Describe the concept of serverless computing.",
    "How does blockchain technology work?",
    "What are the advantages of microservices architecture?",
    "Explain the concept of DevOps and its benefits.",
    "What are the key considerations for API security?",
    "How does natural language processing work?",
    "What is the role of big data in modern business?",
    "Describe the Internet of Things (IoT) and its applications.",
    "What are the principles of user-centered design?",
    "How can companies implement effective data governance?",
    "Explain the concept of continuous integration and deployment.",
    "What are the benefits of containerization with Docker?",
    "How does quantum computing differ from classical computing?",
]

system_prompts = [
    "You are a helpful AI assistant providing concise information.",
    "You are a technical expert explaining complex concepts clearly.",
    "You are a business consultant offering strategic insights.",
    "You are a marketing specialist providing creative ideas.",
    "You are a data analyst explaining insights from information.",
]

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate sample Bedrock logs")
    parser.add_argument("--profile", type=str, default="default",
                        help="AWS profile to use for Bedrock API calls")
    return parser.parse_args()

args = parse_arguments()
profile = args.profile

# Create a Bedrock runtime client with the specified profile
try:
    session = boto3.Session(profile_name=profile)
    bedrock_runtime = session.client("bedrock-runtime")
    logger.info(f"Successfully created Bedrock runtime client using profile: {profile}")  # noqa: G004
except Exception as e:
    logger.exception(f"Failed to create Bedrock runtime client: {e!s}")  # noqa: G004, TRY401
    raise

# Choose a model that's available to your account
model_id = "us.amazon.nova-micro-v1:0"  # Use a model available in your account

# Function to generate random metadata
def generate_random_metadata():
    tenant_id = random.choice(tenants)
    company = random.choice(companies)
    department = random.choice(departments)
    cost_center = random.choice(cost_centers)
    use_case = random.choice(use_cases)
    environment = random.choice(environments)

    return {
        "TenantID": tenant_id,
        "Company": company,
        "Department": department,
        "CostCenter": cost_center,
        "UseCase": use_case,
        "Environment": environment,
        "ApplicationID": f"{department.lower()}-app",
        "Region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
        "requestId": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
    }

# Run 50 different calls to populate logs
def run_multiple_calls(n=2):
    results = []
    print(f"# Running {n} calls to Bedrock Converse API")

    start_time = time.time()

    for i in range(n):
        # Generate unique metadata for this call
        metadata = generate_random_metadata()

        # Select a random prompt and system prompt
        prompt = random.choice(prompts)
        system_prompt = random.choice(system_prompts)

        try:
            # Display progress
            print(f"### Call {i+1}/{n}")
            #print(f"Tenant: {metadata['tenantId']} | Company: {metadata['company']} | Department: {metadata['department']}")
            #print(f"Prompt: {prompt}")

            # Make the API call
            response = generate_conversation(
                client=bedrock_runtime,
                model_id=model_id,
                system_prompt=system_prompt,
                prompt=prompt,
                metadata=metadata,
            )

            # Extract text from response
            response_text = ""
            for content_block in response["content"]:
                if "text" in content_block:
                    response_text = content_block["text"]
                    break

            # Display a shortened version of the response
            response_length = 150
            shortened_response = response_text[:150] + "..." if len(response_text) > response_length else response_text
            #print(f"Response: {shortened_response}")

            # Add to results
            results.append({
                "metadata": metadata,
                "prompt": prompt,
                "response": shortened_response,
                "success": True,
            })

            # Add a small delay between requests to avoid rate limiting
            delay = random.uniform(0.5, 2.0)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)

        except Exception as e:
            logger.exception(f"Failed on request {i+1}: {e!s}")  # noqa: G004, TRY401
            results.append({
                "metadata": metadata,
                "prompt": prompt,
                "error": str(e),
                "success": False,
            })
            # Continue with next request after a longer delay
            time.sleep(5)

    end_time = time.time()
    total_time = end_time - start_time

    # Summary statistics
    successful_calls = sum(1 for r in results if r["success"])
    print("## Summary")
    print(f"- Total calls: {n}")
    print(f"- Successful calls: {successful_calls}")
    print(f"- Failed calls: {n - successful_calls}")
    print(f"- Total time: {total_time:.2f} seconds")
    print(f"- Average time per call: {total_time/n:.2f} seconds")

    # Count by companies and departments
    company_counts = {}
    department_counts = {}
    for r in results:
        if not r["success"]:
            continue
        company = r["metadata"]["Company"]
        department = r["metadata"]["Department"]
        company_counts[company] = company_counts.get(company, 0) + 1
        department_counts[department] = department_counts.get(department, 0) + 1

    print("### Distribution by Company")
    for company, count in company_counts.items():
        print(f"- {company}: {count} calls")

    print("### Distribution by Department")
    for dept, count in department_counts.items():
        print(f"- {dept}: {count} calls")

    return results

# Run the calls
results = run_multiple_calls(50)
