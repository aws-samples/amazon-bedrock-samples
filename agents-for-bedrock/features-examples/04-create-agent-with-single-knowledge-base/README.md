# Creating Agent with a Single Knowledge Base

In this folder, we provide an example of creating an agent with Amazon Bedrock and 
integrating it with [Knowledge Bases for Amazon Bedrock](https://aws.amazon.com/bedrock/knowledge-bases/). 
With this integration, the agent will be able to respond to a user query by taking a sequence of actions, 
consulting the knowledge base to obtain more information, and finally responding to the user with an answer.

![Agents with Knowledge Bases for Amazon Bedrock](agents-with-kb.png)

In this notebook you will learn how to create an Amazon Bedrock Agent that makes use of Knowledge Bases 
for Amazon Bedrock to retrieve data and answer questions about this data. 
The use case for this notebook is an Amazon Bedrock Assistant, an Agent that answers questions about Bedrock's documentation.

This involves the following steps:

1. Import the needed libraries
2. Upload the dataset to Amazon S3
3. Create the Knowledge Base for Amazon Bedrock
4. Create the Agent for Amazon Bedrock
5. Test the Agent
6. Clean-up the resources created


For more details on __agents__ see [Agents for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html).

For more details on __Knowledge Bases__ see [Knowledge bases for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) 

