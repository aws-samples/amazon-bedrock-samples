# Task Automation Using Agents and Knowledge Base for Amazon Bedrock - Insurance Agent. 
---

## Content
- [Overview](#overview)
- [Agents and Knowledge Base Architecture](#agents-and-knowledge-base-architecture)
- [Deployment Guide](#deployment-guide)
- [Testing and Validation](#testing-and-validation)
- [Clean Up](#clean-up)

## Overview

You can now use [Agents for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) and [Knowledge base for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) to configure specialized agents that seamlessly execute actions based on user input and your organization's data. These managed agents play conductor, orchestrating interactions between foundation models, API integrations, user conversations, and knowledge bases loaded with your data. Agents and knowledge bases allow you to **build on existing enterprise resources** to enhance user experience and automate repetitive tasks.

This insurance agent sample solution combines an Agent and Knowledge base for Amazon Bedrock to automate insurance claim lifecycle actions like creating new claims, sending pending document reminders for open claims, gathering claims evidence, and searching for information on existing claims.

## Agents and Knowledge Base for Amazon Bedrock

### Agents and Knowledge Base Functionality
Agents and Knowledge Base for Amazon Bedrock work together to provide the following set of capabilities:

- **Task Decomposition:** Agents expand foundation models to comprehend user inquiries and dissect tasks into manageable steps for execution.
- **Interactive Data Collection:** Agents engage in natural conversations to gather supplementary information from users.
- **Task Execution:** Agents fulfill customer requests through series of reasoning steps and corresponding actions based on [ReAct prompting](https://www.promptingguide.ai/techniques/react).
- **System Integration:** Agents make API calls to internal company systems to execute specific action groups.
- **Data Querying:** Knowledge bases enhance accuracy and performance through fully-managed [retrieval augmented generation (RAG)](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models-customize-rag.html) using customer specific data sources.
- **Source Attribution:** Agents conduct source attribution, identifying and tracing the origin of information or actions.

### Agents and Knowledge Base Architecture

<p align="center">
  <img src="design/agent-overview.png">
  <em>Diagram 1: Agents and Knowledge Base for Amazon Bedrock Architecture Overview</em>
</p>

1. Users provide natural language inputs to the agent.

    **Sample Prompts:**
    - _Create a new claim._
    - _Send a pending documents reminder to the policy holder of claim ID 2s34w-8x._
    - _Gather evidence for claim ID 5t16u-7v._
    - _What is the total claim amount for claim ID 3b45c-9d?_
    - _What is the total repair estimate for claim ID 3b45c-9d?_
    - _What factors determine my car insurance premium?_
    - _How can I lower my car insurance rates?_
    - _Which claims have open status?_
    - _Send pending document reminders to all policy holders with open claims._
      
2. During **pre-processing**, the agent validates, contextualizes, and categorizes user input. The user input (or _Task_) is interpreted by the agent using chat history and the instructions and underlying foundation model that were specified during [agent creation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-create.html). The agent's [instructions](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) are descriptive guidelines outlining the agent's intended actions. Also, you can optionally configure [advanced prompts](https://docs.aws.amazon.com/bedrock/latest/userguide/advanced-prompts.html), which allow you to boost your agent's precision by employing more detailed configurations and offering manually selected examples for few-shot prompting. This method allows you to enhance the model's performance by providing labeled examples associated with a particular task. 

3. During **orchestration**, the agent develops a _rational_ with the logical steps of which action group API invocations and knowledge base queries are needed to generate an _observation_ that can be used to augment the base prompt for the underlying foundation model. This ReAct style of prompting serves as the input for activating the foundation model, which then anticipates the most optimal sequence of actions to complete the user's task.

4. [Action groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-setup.html) are a set of APIs and corresponding business logic, whose OpenAPI schema is defined as JSON files stored in S3. The schema allows the agent to reason around the function of each API. Each action group can specify one or more API paths, whose business logic is executed through the Lambda function associated with the action group.

5. [Knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) provide fully-managed RAG to supply the agent with access to your data. You first configure the knowledge base by specifying a description that instructs the agent when to use your knowledge base. Then you point the knowledge base to your Amazon S3 data source. Finally, you specify your existing vector store or allow Bedrock to create the vector store on your behalf. Once configured, each [data source sync](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ingest.html) creates vector embeddings of your data that the agent can use to return information to the user or augment subsequent foundation model prompts.

6. During **post-processing**, once all _orchestration_ iterations are complete, the agent curates a final response. 

## Deployment Guide
see [Deployment Guide](documentation/deployment-guide.md)

## Testing and Validation
see [Testing and Validation](documentation/testing-and-validation.md)

## Clean Up
see [Clean Up](documentation/clean-up.md)

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
