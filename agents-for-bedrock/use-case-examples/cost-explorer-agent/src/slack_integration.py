import os
import json
import boto3
from botocore.exceptions import ClientError
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger
from botocore.config import Config

# Initialize logger
logger = Logger()

# Function to retrieve secrets from AWS Secrets Manager
def get_secret(secret_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(f"Error retrieving secret: {str(e)}")
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            return get_secret_value_response['SecretString']
        else:
            return base64.b64decode(get_secret_value_response['SecretBinary'])


# Retrieve secrets from AWS Secrets Manager
try:
    secrets = json.loads(get_secret(os.environ["SLACK_SECRETS"]))
    SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
    SLACK_SIGNING_SECRET = secrets["SLACK_SIGNING_SECRET"]
except Exception as e:
    logger.error(f"Failed to retrieve secrets: {str(e)}")
    raise

# Initialize AWS clients
config = Config(read_timeout=1000)
bedrock_agent_client = boto3.client(
    service_name='bedrock-agent-runtime', config=config)

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET,
          process_before_response=True)

# Middleware to log requests


@app.middleware
def log_request(logger, body, next):
    logger.debug(body)
    next()  # Call the next middleware or listener


command = "/billing-agent"

# Function to acknowledge the request within 3 seconds


def respond_to_slack_within_3_seconds(body, ack):
    text = None
    if 'text' in body:
        # For slash command
        text = body.get("text")
    elif 'event' in body and 'text' in body['event']:
        # For app_mention event
        text = body['event'].get("text")
    if text is None or len(text) == 0:
        ack(f":x: Usage: {command} (description here)")
    else:
        ack(f"Accepted! (task: {text})")


def invoke_bedrock_agent(input_text, session_id):
    try:
        response = bedrock_agent_client.invoke_agent(
            agentId=os.environ["BEDROCK_AGENT_ID"],
            agentAliasId=os.environ["BEDROCK_AGENT_ALIAS_ID"],
            sessionId=session_id,
            inputText=input_text
        )

        completion = ""
        for event in response.get("completion", []):
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode('utf-8')
            # Check for failure trace
            elif 'trace' in event and 'trace' in event['trace']:
                failure_trace = event['trace']['trace'].get('failureTrace')
                if failure_trace:
                    print(failure_trace)
        return completion
    except Exception as e:
        logger.error(f"Error invoking Bedrock agent: {str(e)}")
        return "Sorry, I encountered an error while processing your request."

# Lazy function for processing the task in the background


def run_long_process(respond=None, say=None, body=None):
    text = None
    user = None
    thread_ts = None

    # Check for text in both slash command and app_mention event
    if 'text' in body:
        text = body.get("text")
        # For slash commands, use the command's ts as thread_ts
        thread_ts = body.get("ts")
    elif 'event' in body and 'text' in body['event']:
        text = body['event'].get("text")
        user = body['event'].get("user")
        thread_ts = body['event'].get("thread_ts") or body['event'].get("ts")

    # Generate a unique session ID (you might want to implement a more robust method)
    session_id = f"session_{thread_ts}"

    # Invoke Bedrock agent
    agent_response = invoke_bedrock_agent(text, session_id)

    # Check if we are dealing with a slash command (respond) or an event (say)
    if respond:
        respond(agent_response)
    elif say and user:
        say(f"<@{user}> {agent_response}", thread_ts=thread_ts)


# Command listener for '/billing-agent'
app.command(command)(
    ack=respond_to_slack_within_3_seconds,
    lazy=[run_long_process]
)

# Event listener for 'app_mention'
app.event("app_mention")(
    ack=respond_to_slack_within_3_seconds,
    lazy=[lambda body, say: run_long_process(say=say, body=body)]
)

# AWS Lambda handler
def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)