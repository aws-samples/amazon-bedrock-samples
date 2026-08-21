# OpenAI Responses API with Amazon Bedrock

This sample demonstrates how to use the OpenAI Python SDK with the Amazon Bedrock `bedrock-mantle` endpoint. It covers model discovery, privacy-conscious requests, stored multi-turn state, response retrieval, streaming, background processing, error handling, and cleanup.

## Run the sample

1. Generate an Amazon Bedrock API key in a supported AWS Region.
2. Optionally export configuration:

   ```bash
   export AWS_REGION="us-east-1"
   export BEDROCK_MODEL_ID="openai.gpt-oss-120b"
   ```

3. Open `bedrock_mantle_openai_responses_api.ipynb` in Jupyter or SageMaker Studio.
4. Run the notebook from top to bottom.

The notebook prompts for the key without displaying it when `OPENAI_API_KEY` is unset. In automated environments, inject `OPENAI_API_KEY` through the environment's secret-management facility instead of placing it in a shell script or notebook.

## Security

- Never commit an API key or save it in notebook output.
- Use long-term keys only for exploration.
- Prefer short-term keys and least-privilege IAM policies for production.
- Set `store=False` explicitly when Amazon Bedrock should not retain response state.

## References

- [Inference using the Responses API](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-reference.html)
- [API compatibility by model](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html)
- [Amazon Bedrock Projects](https://docs.aws.amazon.com/bedrock/latest/userguide/projects.html)
- [Bedrock Mantle quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas-mantle.html)
