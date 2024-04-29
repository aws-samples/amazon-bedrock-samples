# Prompt and Session Attributes

In this folder, we provide an example of an HR agent using Agents for Amazon Bedrock with prompt and session attributes

For greater control of session context, you can modify the SessionState object in your agent. The SessionState object contains two types of attributes that you can use to provide conversational context for the agent during user conversations.

__sessionAttributes__ – Attributes that persist over a session between a user and agent. All InvokeAgent requests made with the same sessionId belong to the same session, as long as the session time limit (the __idleSessionTTLinSeconds__) has not been surpassed.

__promptSessionAttributes__ – Attributes that persist over a single turn (one InvokeAgent call). You can use the $prompt_session_attributes$ placeholder when you edit the orchestration base prompt template. This placeholder will be populated at runtime with the attributes that you specify in the promptSessionAttributes field.

Here is the general format of the session state object:

```json
{
    "sessionAttributes": {
        "<attributeName1>": "<attributeValue1>",
        "<attributeName2>": "<attributeValue2>",
        ...
    },
    "promptSessionAttributes": {
        "<attributeName3>": "<attributeValue3>",
        "<attributeName4>": "<attributeValue4>",
        ...
    }
}
```

You can set session attributes at the follwing steps:

1. When you set up an action group and write the Lambda function, include sessionAttributes or promptSessionAttributes in the response event that is returned to Amazon Bedrock.

2. During runtime, when you send an InvokeAgent request, include a sessionState object in the request body to dynamically change the session state attributes in the middle of the conversation.

As an example, we can set __sessionAttributes__ for first name. So when a user uses your application and provides their first name, your code will send the first name as a session attribute and the agent will store their first name for the duration of the session. These attributes can be used downstream in the lambda function calls associated with an action group.


```json
{
    "inputText": "<request>",
    "sessionState": {
        "sessionAttributes": {
            "firstName": "<first_name>"
        }
    }
}
```

In addition, if we can also modify session context through __promptSessionAttributes__. We can retrieve the time zone at the user's location if the user uses a word indicating relative time (such as "tomorrow") in the <request>, and store in a variable called <timezone>. Then, if a user asks to book a hotel for tomorrow, your code sends the user's time zone to the agent and the agent can determine the exact date that "tomorrow" refers to.

```json
{
    "inputText": "<request>",
    "sessionState": {
        "promptSessionAttributes": {
            "timeZone": "<timezone>"
        }
    }
}

```


For more details on session attributes, please see [Control session context](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-session-state.html) 