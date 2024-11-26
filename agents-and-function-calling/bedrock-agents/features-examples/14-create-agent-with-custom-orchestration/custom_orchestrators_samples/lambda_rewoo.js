exports.handler = async (event, context) => {
    console.log(`The incoming event: ${JSON.stringify(event)}`);

    validateEvent(event);

    const state = event.state;
    console.log(`Current state: ${state}`);

    const eventResponse = nextEvent(event);
    console.log(`Response Event: ${eventResponse}`);
    return eventResponse;
};

function validateEvent(event) {
    if (!event || !event.state) {
        throw new Error('Invalid event structure: missing state');
    }
    if (!event.context) {
        throw new Error('Invalid event structure: missing context');
    }
}

function nextEvent(event) {
    const incomingState = event.state;
    let state = {};

    if (incomingState === 'START') {
        const responseEvent = 'INVOKE_MODEL';
        const responseTrace = "This is on start debug trace!";
        const payloadData = JSON.stringify(createPrompt(event, createPlanningSystemPrompt));

        return createPayload(payloadData, responseEvent, responseTrace, event.context);

    } else if (incomingState === 'MODEL_INVOKED') {
        if (isEndState(event)) {
            const responseEvent = 'FINISH';
            const responseTrace = "This is on finish debug trace!";
            const payloadData = JSON.stringify(getEndTurnPayload(event));
            return createPayload(payloadData, responseEvent, responseTrace, event.context);
        } else {
            const responseEvent = 'INVOKE_TOOL';
            const responseTrace = "This is on tool use debug trace!";
            const [payloadData, _state] = executePlanOnGeneration(event);
            return createPayload(JSON.stringify(payloadData), responseEvent, responseTrace, {
                sessionAttributes: {
                    state: JSON.stringify(_state)
                }
            });
        }

    } else if (incomingState === 'TOOL_INVOKED') {
        const [payloadData, _state] = continueExecution(event);
        if (payloadData) {
            const responseEvent = 'INVOKE_TOOL';
            const responseTrace = "This is on tool use debug trace!";
            return createPayload(JSON.stringify(payloadData), responseEvent, responseTrace, {
                sessionAttributes: {
                    state: JSON.stringify(_state)
                }
            });
        } else {
            state = {
                plan: null,
                tool_state: {
                    last_tool_used: null,
                    parent_tool_result: null,
                    last_tool_result: null,
                    is_summary: true
                }
            };
            const responseEvent = 'INVOKE_MODEL';
            const responseTrace = "This is on model invocation debug trace!";
            const payloadData = JSON.stringify(createPrompt(event, createSummarySystemPrompt));
            return createPayload(payloadData, responseEvent, responseTrace, {
                sessionAttributes: {
                    state: JSON.stringify(state)
                }
            });
        }

    } else {
        throw new Error('Invalid state provided!');
    }
}

function continueExecution(event) {
    const _state = JSON.parse(event.context.sessionAttributes.state || '{}');
    const _plan = _state.plan;
    const _tool_state = _state.tool_state;
    const _tool_result = JSON.parse(event.input.text).toolResult;
    
    _tool_state.last_tool_result = _tool_result.content[0].text;
    if (!_tool_state.parent_tool_result) {
        _tool_state.parent_tool_result = _tool_result.content[0].text;
    }

    const [tool_to_use, function_signature, parent_tool_result] = getToolToExecute(_plan, _tool_state);
    const _current_plan = _plan;

    if (tool_to_use) {
        _state.plan = _current_plan;
        _state.tool_state = {
            last_tool_used: function_signature,
            parent_tool_result: parent_tool_result,
            last_tool_result: null,
            is_summary: false
        };
        return [tool_to_use, _state];
    }
    return [null, null];
}

function executePlanOnGeneration(event) {
    const _plan = JSON.parse(event.input.text).output.content[0].text.replace('\n', '');
    const [tool_to_use, function_signature, parent_tool_result] = getToolToExecute(_plan);
    const _state = {
        plan: _plan,
        tool_state: {
            last_tool_used: function_signature, 
            parent_tool_result,
            last_tool_result: parent_tool_result,
            is_summary: false
        }
    };
    return [tool_to_use, _state];
}

function getToolToExecute(_plan, _tool_state = null) {
    const matches = /<plan>(.*?)<\/plan>/s.exec(_plan);
    if (!matches) return [null, null, null];

    const effective_plan = matches[1].trim();
    const steps = effective_plan.match(/<step_\d+>.*?<\/step_\d+>/gs);
    if (!steps) return [null, null, null];

    let to_continue_process = false;

    for (const step of steps) {
        if (step.includes('fn::')) {
            const [variable_name, function_name] = parseFunction(step);
            
            if (_tool_state && _tool_state.last_tool_used === function_name && !to_continue_process) {
                to_continue_process = true;
                continue;
            }

            if (_tool_state && !to_continue_process) {
                continue;
            }

            const parent_tool_result = _tool_state ? _tool_state.parent_tool_result : null;
            return [createToolUse(function_name), function_name, parent_tool_result];
        }

        const for_matches = /<for[^>]*>(.*?)<\/for>/s.exec(step);
        if (for_matches) {
            // For loop handling logic would go here similar to Python version
            // This is simplified
            return [null, null, null];
        }
    }
    return [null, null, null];
}

function parseFunction(step) {
    const matches = /(.*?)fn::([^(]+)\((.*?)\)/.exec(step);
    if (!matches) return [null, null];
    const variable_name = matches[1].replace('=', '').trim();
    const function_name = `fn::${matches[2].trim()}(${matches[3].trim()})`;
    return [variable_name, function_name];
}

function createToolUse(function_name) {
    const matches = /([^(]+)\((.*?)\)/.exec(function_name);
    const params = {};
    matches[2].split(',').forEach(param => {
        const [key, value] = param.trim().split('=');
        params[key.trim()] = value.trim();
    });

    return {
        toolUse: {
            toolUseId: crypto.randomUUID(),
            name: matches[1].replace('fn::', '').trim(),
            input: params
        }
    };
}

function isEndState(event) {
    try {
        const stateStr = event?.context?.sessionAttributes?.state;
        if (!stateStr) return false;
        const _state = JSON.parse(stateStr);
        return _state?.tool_state?.is_summary || false;
    } catch (e) {
        console.error("Error in isEndState:", e);
        return false;
    }
}

function getEndTurnPayload(event) {
    const json_input = JSON.parse(event.input.text);
    return json_input.output.content[0].text;
}

function createPrompt(event, createPromptFunction) {
    const messages = constructMessages(event.context, event.input, createPromptFunction);
    return createConverseApiPrompt(event.context, messages);
}

function createPayload(payloadData, actionEvent, traceData, context = {}) {
    return {
        version: "1.0",
        actionEvent,
        output: {
            text: payloadData,
            trace: {
                event: {
                    text: traceData
                }
            }
        },
        context: {
            sessionAttributes: context?.sessionAttributes || {},
            promptSessionAttributes: context?.promptSessionAttributes || {}
        }
    };
}

function createConverseApiPrompt(context, messages) {
    const model_id = context.agentConfiguration?.defaultModelId;
    const tools = context.agentConfiguration?.tools;

    return {
        modelId: model_id,
        messages,
        inferenceConfig: {
            maxTokens: 500,
            temperature: 0,
            topP: 0.9
        },
        toolConfig: {
            tools
        }
    };
}

function constructMessages(context, input, createPromptFunction) {
    const conversations = context.session || [];
    const messages = [];

    for (const turn of conversations) {
        if (turn) {
            const steps = turn.intermediarySteps || [];
            for (const step of steps) {
                if (step) {
                    const input = step.orchestrationInput;
                    const output = step.orchestrationOutput;

                    if (input.state === "START") {
                        messages.push(message('user', {text: input.text}));
                    }

                    if (createPromptFunction === createSummarySystemPrompt) {
                        if (input.state === 'MODEL_INVOKED') {
                            messages.push(JSON.parse(input.text).output);
                        }
                        if (input.state === 'TOOL_INVOKED') {
                            messages.push(message('user', JSON.parse(input.text)));
                        }
                        if (output.event === 'INVOKE_TOOL') {
                            messages.push(message('assistant', JSON.parse(output.text)));
                        }
                    }
                }
            }
        }
    }

    if (input) {
        const text = JSON.parse(input.text);
        let messageContent = text;
        if (text.text) {
            if (createPromptFunction === createSummarySystemPrompt) {
                messageContent = {text: `${text.text}\n\n${createPromptFunction(context)}`};
            } else if (createPromptFunction === createPlanningSystemPrompt) {
                messageContent = {text: `${createPromptFunction(context)}\n\n${text.text}`};
            }
        }
        messages.push(message("user", messageContent));
    }

    return mergeConversationTurn(messages, context);
}

function mergeConversationTurn(messages, context) {
    if (!messages.length) return messages;
    
    const model_id = context.agentConfiguration?.defaultModelId?.toLowerCase();
    const merged = [];
    let lastRole = '';

    for (const msg of messages) {
        if (lastRole === msg.role) {
            merged[merged.length - 1].content = msg.content;
        } else {
            merged.push(msg);
        }
        lastRole = msg.role;
    }
    return merged;
}

function message(role, content) {
    return {
        role,
        content: [content]
    };
}

function createPlanningSystemPrompt(context) {
    let promptVars = '';
    if (context.promptSessionAttributes) {
        for (const [key, value] of Object.entries(context.promptSessionAttributes)) {
            promptVars += `<context><key>${key}</key><value>${value}</value></context>`;
        }
    }

    return `
${context.agentConfiguration?.instruction}
Create a structured execution plan using the following format:

<plan>
    <step_[number]> operation </step_[number]>
</plan>

Rules:
1. Each step must contain exactly one function call or control structure
2. Function calls syntax: result=fn::FunctionName(param=value)
3. Control structures:
   - For loops: 
     <for expression="item in collection">
         operation
     </for>
   - If conditions:
     <if expression="condition">
         operation
     </if>

4. Variable assignments must use '='
5. Return statements must be in final step
6. All steps must be numbered sequentially
7. Each operation must be self-contained and atomic

Example:
Input: Process items with function X(input=A)->B then Y(input=B)->C

<plan>
    <step_1>
        results = []
        <for expression="item in items">
            B=fn::X(input=item)
            C=fn::Y(input=B)
            results.append(C)
        </for>
    </step_1>
    <step_2> return results </step_2>
</plan>
<guidelines>
- Never assume any parameter values while invoking a function. 
- You should always provide the value of parameters to the plan, do not abstract it away as variables.
</guidelines>

Please provide the execution plan following these specifications.
Here are some context information that you can use while creating the plan:
${promptVars}
`;
}

function createSummarySystemPrompt(context) {
    return "Given the previous conversation, answer the user's question.";
}


function findValue(string, key) {
    const results = [];
    
    let values = string.match(new RegExp(`"(.*?)${key}(.*?)"(.*?):(.*?)"(.*?)"`, 'g'));
    if (values) {
        values.forEach(value => {
            const match = value.match(new RegExp(`"(.*?)${key}(.*?)"(.*?):(.*?)"(.*?)"`));
            if (match && typeof match[5] === 'string') {
                results.push(`"${match[5]}"`);
            } else if (match) {
                results.push(match[5]);
            }
        });
    }

    values = string.match(new RegExp(`"(.*?)${key}(.*?)"(.*?)=(.*?)"(.*?)"`, 'g'));
    if (values) {
        values.forEach(value => {
            const match = value.match(new RegExp(`"(.*?)${key}(.*?)"(.*?)=(.*?)"(.*?)"`));
            if (match && typeof match[5] === 'string') {
                results.push(`"${match[5]}"`);
            } else if (match) {
                results.push(match[5]);
            }
        });
    }

    return results;
}

function parseTool(planStep) {
    const currentPlan = planStep.trim();
    const variableName = currentPlan.match(/(.*?)fn::/)[1].replace('=', '').trim();
    const functionPart = currentPlan.match(/(.*?)fn::(.*)/)[2].trim();
    return [variableName, functionPart];
}

function checkInputText(event) {
    return JSON.parse(event.input.text).text === "send payload";
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function streamAgentFinishResponse(event) {
    const dataStream = [
        "I", " am", " custom", " orchestation.", "\n", "You chose", " t", "o", " test", " strea", "ming", " from", " lamb", "da", " function", "!"
    ];
    
    const responses = [];
    for (const data of dataStream) {
        const bedrock_stream_answer_tool_data = {
            toolUse: {
                toolUseId: crypto.randomUUID(),
                name: "bedrock_stream_answer_tool",
                input: {
                    text: data
                }
            }
        };
        
        const payload = createPayload(
            JSON.stringify(bedrock_stream_answer_tool_data),
            'INVOKE_TOOL',
            'This is trace on stream_answer_tool',
            event.context
        );
        
        console.log(`Response Event: ${JSON.stringify(payload)}`);
        responses.push(payload);
        await sleep(500);
    }
    return responses;
}

function createGuardrailsPayload(event) {
    const guardrailsConfig = event.context.agentConfiguration.guardrails;
    
    return {
        guardrailIdentifier: guardrailsConfig.identifier,
        guardrailVersion: guardrailsConfig.version,
        source: "INPUT",
        content: [
            {
                text: {
                    text: "hello",
                    qualifiers: ["guard_content"]
                }
            }
        ]
    };
}