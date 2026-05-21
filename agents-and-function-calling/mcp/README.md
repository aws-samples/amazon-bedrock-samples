# bedrock-github-mcp-sample

> **Note:** This example is for demonstration purposes only and is not intended for production use. This sample works well for simple GitHub issues such as dependency updates, documentation fixes, and minor code changes. For complex issues requiring comprehensive testing, users should consider implementing a robust code testing approach with this sample.

This example demonstrates an agent built with Amazon Bedrock, LangGraph that interacts with the GitHub MCP server to automate the process of handling GitHub issues.

**Functionality:**
1.  **Fetch Open Issues:** Retrieves open issues from a specified GitHub repository.
2.  **Analyze Issue:** Uses an LLM to analyze the first fetched issue to determine if code changes are needed, no changes are needed, or clarification is required.
3.  **Plan Changes (if needed):** If code changes are required, uses a ReAct agent (LLM + tools) to explore relevant files and formulate a plan.
4.  **Implement Changes (if needed):** If a plan exists, uses an LLM and GitHub tools to modify the necessary files in a new branch.
5.  **Create Pull Request (if needed):** If files were successfully changed, creates a pull request.
6.  **Handle Other Cases:** Includes nodes to handle scenarios where no code changes are needed or where clarification/errors 



## Prerequisites 

You will need the following prerequisites before you can proceed with this solution. For this post, we use the us-west-2 AWS Region. For details on available Regions, see Amazon Bedrock endpoints and quotas. 
- A valid AWS account. 
- An AWS Identity and Access Management (IAM) role in the account that has sufficient permissions to invoke Bedrock models. If you're planning to run your code on a Amazon SageMaker Jupyter Notebook instance (rather than locally), you'll also need permissions to set up and manage Amazon SageMaker resources. If you have administrator access, no additional action is required. 
- Access to Anthropic Claude 3.5 Haiku in Amazon Bedrock. For instructions, see Access Amazon Bedrock foundation models. 
- Docker or Finch to run GitHub MCP server as a container
- Fine-grained personal access token. The GitHub MCP server can use many of the GitHub APIs, so enable the least permission required for this post. Assign repository permissions for Contents, Issues and Pull requests.
