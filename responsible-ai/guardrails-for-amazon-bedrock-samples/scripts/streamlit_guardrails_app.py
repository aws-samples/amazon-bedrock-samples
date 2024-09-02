import streamlit as st
import boto3
import json
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--guardrail_identifier', type=str, required=True, help='The identifier of the guardrail')
args = parser.parse_args()

# Initialize AWS SDK clients
bedrock_client = boto3.client("bedrock-runtime")

# Set the page config including the title and favicon
bedrock_logo_path = "../images/bedrock_logo.png"  # Update this path to where you save the Bedrock logo
st.set_page_config(page_title="Customer Support Chatbot with Amazon Bedrock Guardrails", page_icon=bedrock_logo_path)

# Display Bedrock logo
st.image(bedrock_logo_path, width=100)

st.title("Customer Support Chatbot with Amazon Bedrock Guardrails")
st.write(
    """
This app allows you to interact with a customer support chatbot. The chatbot is equipped with guardrails to filter out harmful content and ensure safe interactions.
"""
)

# Update the URLs below with your actual blog URL and AWS Guardrails documentation URL
blog_url = "https://medium.com/@mccartni/building-responsible-ai-implementing-bedrock-guardrails-in-your-customer-support-chatbot-f8867088beeb"
aws_guardrails_url = "https://aws.amazon.com/bedrock/guardrails/"

st.markdown(
    f"""
    [![Blog](https://img.shields.io/badge/Medium%20Blog%20Walkthrough-Link-blue)]({blog_url})  
    [![AWS Guardrails Documentation](https://img.shields.io/badge/AWS%20Guardrails%20Documentation-Link-green)]({aws_guardrails_url})
    """
)

# User input section
user_input = st.text_area("Enter your message:", height=100)

# Submit button
if st.button("Submit"):
    if not user_input:
        st.warning("Please enter a message to proceed.")
    else:
        try:
            payload = {
                "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                "contentType": "application/json",
                "accept": "application/json",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_input}
                            ],
                        }
                    ],
                },
            }

            # Convert the payload to bytes
            body_bytes = json.dumps(payload['body']).encode('utf-8')

            response = bedrock_client.invoke_model(
                modelId=payload["modelId"],
                contentType=payload["contentType"],
                accept=payload["accept"],
                body=body_bytes,
                guardrailIdentifier=args.guardrail_identifier,
                guardrailVersion='DRAFT',
                trace="ENABLED"
            )

            response_body = json.loads(response["body"].read().decode("utf-8"))
            
            # Extract and display the text content from the response
            if 'content' in response_body and len(response_body['content']) > 0:
                output_text = " ".join([item['text'] for item in response_body['content'] if item['type'] == 'text'])
            else:
                output_text = 'No text content found in response.'

            st.subheader("Model Response:")
            st.write(output_text)
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Information section
st.sidebar.header("About this App")
st.sidebar.write(
    """
This chatbot is powered by Amazon Bedrock and equipped with several guardrails to prevent the generation of harmful content. The guardrails filter out:
- Sexual content
- Violent content
- Hate speech
- Insults
- Misconduct
- Prompt attacks

Additionally, the chatbot masks or blocks sensitive information such as email addresses, phone numbers, social security numbers, and more.
"""
)
