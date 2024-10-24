
# Creating Agent with Knowledge Base and an Action Group connection

In this folder, we provide an example of creating an agent with Amazon Bedrock and integrating it with a 
Knowledge Base for Amazon Bedrock and with an Action Group. 
With this integration, the agent will be able to respond to a user query by taking a sequence of actions, 
consulting the knowledge base to obtain more information, and/or executing tasks using the lambda function 
connected with an Action Group.


## Agent Architecture
In this example we will create a restaurant assistant agent that connects with a Knowledge Base for Amazon Bedrock containing the restaurant's different menus. 
This agent also connects to an action group that provides functionalities for handling the table booking in this restaurant. 
![Agents architecture - showing an agent responding on one end using APIs and action groups and then on the end responding to other questions with a knowledge base on a vector database](images/architecture.png)

The action group created in this example uses [function details](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-function.html) to define the functionalities for 
`create_booking`, `get_booking_details` and `delete_booking`.
The action group execution connects with a Lambda function that interacts with an Amazon DynamoDB table.

## Build and Deploy with AWS CDK 
The complete provisioning of Amazon Bedrock agent, integration with a Knowledge Base and an Action Group is automated using AWS CDK [Cloud Development Kit](https://aws.amazon.com/cdk/) in [Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html). AWS CDK is used primarily used to provision and manage cloud resources in a programmatic and infrastructure-as-code (IaC) manner.

Developers can leverage their existing skills as CDK supports TypeScript, JavaScript, Python, Java, C#/.Net, and Go programming languages and tools to define infrastructure, leading to faster development cycles. Develop faster by using and sharing reusable components called [constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html). Use high-level constructs to quickly define larger components of your application, with secure defaults for your AWS resources, defining more infrastructure with less code.  It's common to see reductions ranging from 30% to 50% or more in terms of lines of code when moving from notebook-based implementations to CDK. This reduction primarily stems from improved organization, modularity, and abstraction capabilities offered by CDK.

CDK integrates well with CI/CD pipelines (e.g., AWS CodePipeline, CodeBuild). This enables automated testing, deployment, and rollback of infrastructure changes, enhancing reliability and speed of deployments. 

For complex architectures or microservices-based applications, CDK can manage dependencies and relationships between resources, ensuring they are provisioned and configured correctly.CDK promotes adherence to AWS best practices through built-in constructs and libraries. For example, it can enforce secure defaults for IAM policies, VPC configurations, and encryption settings.

This folder contains the complete Python CDK code for of Amazon Bedrock agent, integration with a Knowledge Base and with an Action Group.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

### Python Setup

This project is set up like a standard Python project. The initialization process also needs a virtualenv within this project, stored under the `.env` directory. To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package.

Manually create a virtualenv on MacOS and Linux:

```
python3 -m venv .env
```

After the bootstrap process completes and the virtualenv is created, use the following step to activate your virtualenv.

```
source .env/bin/activate
```

If you are a Windows platform, activate the virtualenv like this:

```
.env\Scripts\activate.bat
```

Once the virtualenv is activated, install the required dependencies.

```
pip3 install -r requirements.txt
```
Install AWS [GenAI CDK constructs](https://github.com/awslabs/generative-ai-cdk-constructs) for provisioning of Bedrock Knowledgebase and Agent

```
pip3 install cdklabs.generative-ai-cdk-constructs
```
### CDK Synthesize

Now synthesize the CloudFormation template for this code. This will generate the CloudFormation template for you to examine, and verify that your setup is complete.

```
cdk synth
```

### CDK Deploy

You use `cdk deploy` actually to create the resources with default parameters and their values.

```
cdk deploy
```

### CDK Deploy with Parameters (Optional)

You use `cdk deploy` with parameters with your own set of values to create the resources.

![Supported Parameters - shows the list of supported parameters for cdk deploy](images/cdk-parameters.png)

Note: AgentModelId with claude-3-sonnet and EmbeddingModelId with titan-embed-text-v2 are only supported in this example.

You can select and decide to use the number of supported parameters shown as examples below

```
cdk deploy BedrockagentStack --parameters AgentName=<user input>

cdk deploy BedrockagentStack --parameters AgentName=<user input>, AgentAliasName=<user input> , KnowledgeBaseName=<user input> , S3BucketName=<user input> , AgentModelId=<user input> , EmbeddingModelId=<user input>

```

### Test the Agent

Ask questions to Hotel booking agent:  

Invoke Agent to query Knowledge Base  
Q: What are the starters in the childrens menu?   

Invoke Agent to execute function from Action Group  
Q: Hi, I am Anna. I want to create a booking for 2 people, at 8pm on the 5th of August 2024.   

Invoke Agent with prompt attribute   
Q: I want to create a booking for 2 people, at 8pm on the 5th of May 2024   

Validating prompt attribute   
Q: What was the name used in my last reservation?    

Retrieving information from the database in a new session  
Q: I want to get the information for booking 007659d1    

Canceling reservation  
Q: I want to delete the booking 007659d1  

Handling context with PromptAttributes  
Q: I want to create a booking for 2 people, at 8pm tomorrow.  

Important: remember to replace the booking id with the new one  
Q:I want to get the information for booking 98e6464f  


### CDK Destroy

You use `cdk destroy` to remove the resources you created with `cdk deploy`.

```
cdk destroy
```

Enjoy!
