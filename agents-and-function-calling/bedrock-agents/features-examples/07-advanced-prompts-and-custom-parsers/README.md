# Advanced Prompts and Custom Lambda Parsers

In this folder, we provide an example of an HR agent using [Amazon Bedrock Agents](https://aws.amazon.com/bedrock/agents/) new advanced prompt and custom lambda parser capabilities.

Agents in Amazon Bedrock take a sequence of steps to process a user query: Pre-processing, Orchestration, Knowledge base response generation, and Post-processing. For each step in the sequence Prompt templates are the basis for creating prompts to be provided to the FM. Amazon Bedrock Agents exposes the default four base prompt templates that are used during the pre-processing, orchestration, knowledge base response generation, and post-processing. You can optionally edit these base prompt templates to customize your agent's behavior at each step of its sequence. This forms the basis for Advanced prompts.

For example, to create a custom pre-processing prompt we can provide the __custom prompt__ string in the __promptOverrideConfiguration__ object in the __UpdateAgent__ call.


```python
"promptOverrideConfiguration": { 
    "promptConfigurations": [ 
        { 
            "basePromptTemplate": <custom_prompt:string>,
            "inferenceConfiguration": { 
                "maximumLength": int,
                "stopSequences": [ "string" ],
                "temperature": float,
                "topK": float,
                "topP": float
            },
            "promptCreationMode": "OVERRIDDEN",
            "promptState": "ENABLED",
            "promptType": "PRE_PROCESSING"
        }
    ]
}
```

In addition, we can provide custom lambda parsers to modify the raw output from the LLM at each of the steps in the agent sequence. This custom lambda parser is often used in conjunction with the custom prompt to give you greater control of not only how process the user query at that step but also 
what parts of the output response should be passed onto the next step in the sequence.

To take advantage of custom lambda parsers, a lambda function needs to be created and used to update the agent using the __UpdateAgent__ call. For our pre-processing example, we can provide the lambda arn  to the __overrideLambda__ key in the __promptOverrideConfiguration__ object in the __UpdateAgent__ call, setting the __parserMode__ to __OVERRIDDEN__.

```python

promptOverrideConfiguration={
        'overrideLambda':parser_arn,
        'promptConfigurations': [
            {
                'basePromptTemplate': custom_pre_prompt,
                'inferenceConfiguration': {
                "maximumLength": 2048,
                "stopSequences": [
                        "</invoke>",
                        "</answer>",
                        "</error>"
                                  ],
                "temperature": 0.0,
                "topK": 250,
                "topP": 1.0,
                },
                'promptCreationMode':'OVERRIDDEN',
                'promptState': 'ENABLED',
                'promptType': 'PRE_PROCESSING',
                'parserMode': 'OVERRIDDEN'
            }
        ]
    }
```

The lambda function provided as the parser needs to respect the structure of event that is produced by  the agent as input as well as respect the structure the agent expects as response from the lambda. Examples of the input and output structure are shown below:

Lambda input event structure:

```json
{
    "messageVersion": "1.0",
    "agent": {
        "name": "string",
        "id": "string",
        "alias": "string",
        "version": "string"
    },
    "invokeModelRawResponse": "string",
    "promptType": "PRE_PROCESSING",
    "overrideType": "OUTPUT_PARSER"
}

```
Lambda response structure for pre-processing:

```json
{
    "messageVersion": "1.0",
    "promptType": "PRE_PROCESSING",
    "preProcessingParsedResponse": {
        "isValidInput": "boolean",
        "rationale": "string"
    }
}
```

For examples of the response structures for the other __promptTypes__ see [Parser Lambda function in Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/lambda-parser.html) 