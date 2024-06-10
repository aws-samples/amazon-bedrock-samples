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
