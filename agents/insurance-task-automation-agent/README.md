# Task Automation Using Agents for Amazon Bedrock - Insurance Agent. 
---

## Content
- [Overview](#overview)
- [Agent Architecture](#agent-architecture)
- [Deployment Guide](#deployment-guide)
- [Testing and Validation](#testing-and-validation)
- [Clean Up](#clean-up)

## Overview

You can now use [Agents for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) and [Knowledge base for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) to configure specialized agents that seamlessly execute actions based on user input and your organization's data. These managed agents play conductor, orchestrating interactions between foundation models, API integrations, user conversations, and knowledge bases loaded with your data. Agents and knowledge bases allow you to **build on existing enterprise resources** to enhance user experience and automate repetitive tasks.

This Insurance agent sample solution creates an Agent for Amazon Bedrock that can assist human Insurance agents by creating a new claim, sending pending document reminders for open claims, and gathering evidence on existing claims.

### Demo Recording
[<img src="design/thumbnail.png" width="100%">](https://www.youtube.com/watch?v=bv4XV7epeik "Task Automation Using Agents for Amazon Bedrock - YouTube")

## Agents and Knowledge Base for Amazon Bedrock

### Agents and Knowledge Base Functionality
Together, Agents and Knowledge Base for Amazon Bedrock functionality encompasses several capabilities:

- **Task Decomposition:** Agents expand foundation models to comprehend user inquiries and dissect tasks into manageable steps for execution.
- **Interactive Data Collection:** Agents engage in natural conversations to gather supplementary information from users.
- **Task Execution:** Agents fulfill customer requests through chain-of-thought reasoning and a series of actions.
- **System Integration:** Agents make API calls to internal company systems to execute specific actions.
- **Data Querying:** Knowledge bases enhance accuracy and performance through fully-managed [retrieval augmented generation (RAG)](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models-customize-rag.html) using customer specific data sources.
- **Source Attribution:** Agents conduct source attribution, identifying and tracing the origin of information or actions.

### Agents and Knowledge Base Architecture

<p align="center">
  <img src="design/agent-overview.png">
  <em>Diagram 1: Agents and Knowledge Base for Amazon Bedrock Architecture Overview</em>
</p>

1. Users provide natural language inputs to the agent.

>> **Sample Prompts:**
- _Create a new claim.
- _Send a pending documents reminder to the policy holder of claim 2s34w-8x.
- _Gather evidence for claim 5t16u-7v.
- _What is the total claims amount for claim 3b45c-9d?
- _What factors determine my car insurance premium?
- _How can I lower my car insurance rates?
- _Send reminders to all policy holders with open claims.
- Create a new claim, provide the injury claim amount for claim 2s34w-8x, and sending pending document reminders to claim_

2. The agent is configured with [instructions](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html), which are descriptive guidelines outlining the agent's intended actions. Additionally, you can optionally configure [advanced prompts](https://docs.aws.amazon.com/bedrock/latest/userguide/advanced-prompts.html), which allow you to boost your agent's precision by employing more detailed configurations and offering manually selected examples for few-shot prompting. This method allows you to enhance the model's performance by providing labeled examples associated with a particular task. The user input is interpreted by the agent using its instructions and underlying foundation model, specified during [agent creation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-create.html). The response workflow is as follows:

    - **Pre-processing:** The agent validates, contextualizes, and categorizes user input. 
    - **Orchestration:** The agent develops a _rational_ with the logical steps of which action group API invocations and knowledge base queries are needed to generate an _observation_ that can be used to augment the base prompt for the underlying foundation model. 
    - **Post-processing:** Once all orchestration iterations are complete, the agent curates a final response.

3. [Action groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-setup.html) are a set of APIs and corresponding business logic, whose OpenAPI schema is defined as JSON files stored in S3. The schema allows the agent to reason around the function of each API. Each action group can specify one or more API paths, whose business logic is executed through the Lambda function associated with the action group.

4. [Knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) provide fully-managed RAG to supply the agent with access to your data. You first configure the knowledge base by specifying a description that instructs the agent when to use your knowledge base. Then you point the knowledge base to your Amazon S3 data source. Finally, you specify your existing vector store or allow Bedrock to create the vector store on your behalf. Once configured, each [data source sync](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ingest.html) creates vector embeddings of your data that the agent can use to return information to the user or augment subsequent foundation model prompts.

## Deployment Guide
see [Deployment Guide](documentation/deployment-guide.md)

## Testing and Validation
see [Testing and Validation](documentation/testing-and-validation.md)

## Clean Up
see [Clean Up](documentation/clean-up.md)

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
