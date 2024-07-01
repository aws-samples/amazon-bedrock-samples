import { v4 as uuidv4 } from 'uuid';
import AWS from 'aws-sdk';
import BedrockLogs from './observability.mjs';
import { BedrockAgentRuntimeClient, RetrieveAndGenerateCommand, InvokeAgentCommand } from "@aws-sdk/client-bedrock-agent-runtime";
import { FirehoseClient } from "@aws-sdk/client-firehose";

AWS.config.update({region: 'us-east-1'});

/* NOTE:Please use your AWS configuration details to fill this section before running the code */

const config = {
  FIREHOSE_NAME: '',
  CRAWLER_NAME: '',
  REGION: 'us-east-1',
  MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  MODEL_ARN: 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
  //KB_ID: '',
  EXPERIMENT_ID: '',
  MAX_TOKENS: 512,
  TEMPERATURE: 0.1,
  TOP_P: 0.9,
  AGENT_ID:'',
  AGENT_ALIAS_ID:'',
  ENABLE_TRACE:true,
  END_SESSION:false,
  SESSION_ID:''
};


/* Here is an example:

const config = {
  FIREHOSE_NAME: 'kb-observability-12345-firehose',
  CRAWLER_NAME: 'GlueCrawler-c1xyjW5vv2JK',
  REGION: 'us-east-1',
  MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  MODEL_ARN: 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
  //KB_ID: 'LSY7MX5WSD',
  EXPERIMENT_ID: '123456789-ABC', // can also be project name
  MAX_TOKENS: 512,
  TEMPERATURE: 0.1,
  TOP_P: 0.9,
  AGENT_ID:'U6THLI9WER',
  AGENT_ALIAS_ID:'W20RFIOASD',
  ENABLE_TRACE:true,
  END_SESSION:false,
  SESSION_ID:'12345'
};
*/

const BedrockAgentClient = new BedrockAgentRuntimeClient({region:'us-east-1'});

var bedrocklogs = new BedrockLogs('local',config['EXPERIMENT_ID'],'Retrieve-and-Generate-with-KB','Agent',true);

const invoke = bedrocklogs.watch({captureInput:true, captureOutput:true, callType:"Retrieve-and-Generate-with-KB"})(async function invoke_agent(question,agent_id,agent_alias_id, 
                session_id, enableTrace, endSession, agent_config=null) {
  
  var inputText;
  var agentId;
  var agentAliasId;
  var sessionId;
  var enableTrace;
  var endSession;
  var event_stream;
  let agent_answer;
  var end_event_received;
  var trace_data;
  
  
   const command = new InvokeAgentCommand({
            inputText:question,
            agentId:agent_id,
            agentAliasId:agent_alias_id,
            sessionId:session_id,
            enableTrace:enableTrace,
            endSession:endSession}
        )
  var agentResponse =  await BedrockAgentClient.send(command);

  event_stream = agentResponse['completion']
  end_event_received = false
  trace_data = []
  agent_answer=''

try {
  for await (const event of event_stream) {
    //console.log('this is event:  ',event)
    if ('chunk' in event) {
      const data = event.chunk.bytes;
      const agentAnswer = new TextDecoder().decode(data);
      agent_answer += agentAnswer;
      end_event_received = true;
    } else if ('trace' in event) {
      const trace = event.trace;
      trace.start_trace_time = Date.now();
      trace_data.push(trace);
    } else {
      throw new Error('Unexpected event.', event);
    }
  }
} catch (err) {
  console.error('Error:', err);
}

  agentResponse['$metadata']['contentType']=agentResponse['contentType']
  agentResponse['$metadata']['sessionId']=agentResponse['sessionId']
  return [agentResponse['$metadata'], agent_answer, trace_data]
});

//return response

var QUESTION = "How many days do I have left to take off during the year for employee 1?"

var response=await invoke(QUESTION, config['AGENT_ID'], config['AGENT_ALIAS_ID'],config['SESSION_ID'],config['ENABLE_TRACE'], config['END_SESSION'])

console.log('This is the full agent observation output',response);