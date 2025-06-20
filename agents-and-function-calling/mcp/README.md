# bedrock-github-mcp-sample

## Prerequisites 

You will need the following prerequisites before you can proceed with this solution. For this post, we use the us-west-2 AWS Region. For details on available Regions, see Amazon Bedrock endpoints and quotas. 
- A valid AWS account. 
- An AWS Identity and Access Management (IAM) role in the account that has sufficient permissions to invoke Bedrock models. If you're planning to run your code on a Amazon SageMaker Jupyter Notebook instance (rather than locally), you'll also need permissions to set up and manage Amazon SageMaker resources. If you have administrator access, no additional action is required. 
- Access to Anthropic Claude 3.5 Haiku in Amazon Bedrock. For instructions, see Access Amazon Bedrock foundation models. 
- Docker or Finch to run GitHub MCP server as a container
- Fine-grained personal access token. The GitHub MCP server can use many of the GitHub APIs, so enable the least permission required for this post. Assign repository permissions for Contents, Issues and Pull requests.
