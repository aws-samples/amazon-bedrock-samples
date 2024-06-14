import { v4 as uuidv4 } from 'uuid';
import AWS from 'aws-sdk';
import BedrockLogs from './observability.mjs';
import { BedrockAgentRuntimeClient, RetrieveAndGenerateCommand } from "@aws-sdk/client-bedrock-agent-runtime";
import { FirehoseClient } from "@aws-sdk/client-firehose";

AWS.config.update({region: 'us-east-1'});


/* NOTE:Please use your AWS configuration details to fill this section before running the code */


const config = {
  FIREHOSE_NAME: '',
  CRAWLER_NAME: '',
  REGION: '',
  MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  MODEL_ARN: 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
  KB_ID: '',
  EXPERIMENT_ID: '',
  MAX_TOKENS: 512,
  TEMPERATURE: 0.1,
  TOP_P: 0.9,
  AGENT_ID:'',
  AGENT_ALIAS_ID:''
};

/* Here is an example:
const config = {
  FIREHOSE_NAME: 'kb-observability-12345-firehose',
  CRAWLER_NAME: 'GlueCrawler-c1xyjW5fg34g',
  REGION: 'us-east-1',
  MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  MODEL_ARN: 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
  KB_ID: 'LSY7MX5QWE',
  EXPERIMENT_ID: '123456789', // can also be project name
  MAX_TOKENS: 512,
  TEMPERATURE: 0.1,
  TOP_P: 0.9,
  AGENT_ID:'U6THLI8HGJ',
  AGENT_ALIAS_ID:'W20RFI0IUY'
};
*/

//const firehoseClient = new FirehoseClient({region:'us-east-1'});
const BedrockAgentClient = new BedrockAgentRuntimeClient({region:'us-east-1'});
//var bedrocklogs = new BedrockLogs(config['FIREHOSE_NAME'],config['EXPERIMENT_ID'],'Retrieve-and-Generate-with-KB','KB',true);
var bedrocklogs = new BedrockLogs('local',config['EXPERIMENT_ID'],'Retrieve-and-Generate-with-KB','KB',false);
async function retrieveAndGenerate(question, params) {
  const input = {
    input: {
      text: question,
    },
    retrieveAndGenerateConfiguration: {
      type: "KNOWLEDGE_BASE",
      knowledgeBaseConfiguration: {
        knowledgeBaseId: config['KB_ID'],
        modelArn: config['MODEL_ARN'],
        generationConfiguration: {
          inferenceConfig: {
            textInferenceConfig: {
              maxTokens: config['MAX_TOKENS'],
              temperature: config['TEMPERATURE'],
              topP: config['TOP_P']
            },
          },
        },
      },
    },
  };

  if ('sessionId' in params) {
    input.sessionId = params['sessionId'];
  }
  const command = new RetrieveAndGenerateCommand(input);
  var response =  await BedrockAgentClient.send(command);
  return response;
}
const test = bedrocklogs.watch({captureInput:true, captureOutput:true, callType:"Retrieve-and-Generate-with-KB"})(async function main(applicationMetadata) {
  const params = {
    'maxTokens': 512,
    'temperature': 0.1,
    'topP': 0.99
  };
  

var response = await retrieveAndGenerate(applicationMetadata['question'], params)
applicationMetadata['model_response'] = response;
Object.assign(applicationMetadata, params);


return response.output.text;
});
var question = 'What is good space themed video game?'
var applicationMetadata = {
  'userID': 'User-1'
};


const dt = new Date().toISOString();
applicationMetadata['request_time'] = dt;
applicationMetadata['model_arn'] = config['MODEL_ARN'];
applicationMetadata['question'] = question;

var response = await test(applicationMetadata);

console.log('The is the response of the watched function',response)
