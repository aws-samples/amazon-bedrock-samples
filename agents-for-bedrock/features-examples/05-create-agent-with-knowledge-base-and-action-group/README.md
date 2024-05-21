# Creating Agent with Knowledge Base and an Action Group connection

In this folder, we provide an example of creating an agent with Amazon Bedrock and integrating it with a Knowledge Base and with an Action Group. 
With this integration, the agent will be able to respond to a user query by taking a sequence of actions, consulting the knowledge base to obtain more information, 
and/or executing tasks using the lambda function connected with an Action Group.

## Agent Architecture
In this example we will create a restaurant assistant agent that connects with a Knowledge Base for Amazon Bedrock containing the restaurant's different menus.
This agent also connects to an action group that provides functionalities for handling the table booking in this restaurant.
![Agents architect](images/agent-architecture.png)

The action group created in this example, uses Feature Definition to define the functionalities for `create_booking`, `get_booking_details` and `delete_booking`.
The action group execution connects with a Lambda function that interacts with an Amazon DynamoDB table.