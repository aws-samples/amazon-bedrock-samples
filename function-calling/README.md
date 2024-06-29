# Function Calling

With function calling, we can provide LLMs with descriptions of tools and functions it can use. An LLM is able to intelligently decide based on user query when and how to use those tools to help answer questions and complete tasks. 

This repository contains examples and use-cases to get you started with Function Calling on Amazon Bedrock


## Contents


- **Amazon Bedrock Converse API function-calling (tool use) examples** - The Converse or ConverseStream API is a unified structured text API action that allows you simplifying the invocations to Bedrock LLMs, using a universal syntax and message structured prompts for any of the supported model providers, and adding support for tool use of function calling with a unified syntax. For more information check the documentation [here](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html) and the API reference [here](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html).


    - Function calling tool use with Converse API in Bedrock:
        * [Notebook](Function_calling_tool_use_with_Converse_API.ipynb)
        * [Streamlit demo](function_calling_converse_bedrock_streamlit.py)

    - Extracting structured JSON with Converse API in Bedrock:
        * [Notebook - Email entity extraction](Extracting_structured_json_Bedrock_converse.ipynb)
        * [Notebook - Adapted version of Anthropic's cookbook](Anthropic_cookbook_extracting_structured_json_Bedrock_converse.ipynb) - Adapted by AWS from the original Anthropic's notebook available [here](https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb).

    - Tool use with Pydantic with Converse API in Bedrock:
        * [Notebook](tool_use_with_pydantic_Bedrock_converse.ipynb)
        * [Script demo](fc_pydantic_class_converse_bedrock.py)

    - Function calling text2SQL with Converse API in Bedrock:
        * [Streamlit demo](function_calling_text2SQL_converse_bedrock_streamlit.py)

    - Function calling migrations with Converse API in Bedrock:
        * [Notebook](fc_migration_from_oai_converse_bedrock.ipynb)
        * [Streamlit demo](fc_migrations_converse_bedrock_streamlit.py)

- **Legacy function calling with Claude 3**
    * [Notebook](./legacy-function-calling-with-Claude.ipynb) - An introduction to function calling using Claude 3



## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
