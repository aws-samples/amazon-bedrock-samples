import { v4 as uuidv4 } from 'uuid';
import AWS from 'aws-sdk';
import {performance} from 'perf_hooks';


/* Defines the class that sets the context for the observability conditions including 
   what feature of Bedrock to observe and log data to return */

class BedrockLogs {
    
    /* Defines the class that sets the context for the observability conditions including 
   what feature of Bedrock to observe and log data to return */
   
    static VALID_FEATURE_NAMES = ["None", "Agent", "KB", "InvokeModel"];

    constructor(deliveryStreamName = null, experimentId = null,defaultCallType = 'LLM', featureName = null,feedbackVariables=false) {
        this.deliveryStreamName = deliveryStreamName;
        this.experimentId = experimentId;
        this.defaultCallType = defaultCallType;
        this.feedbackVariables = feedbackVariables;
        if (featureName !== null) {
            if (!BedrockLogs.VALID_FEATURE_NAMES.includes(featureName)) {
                throw new Error(`Invalid feature_name '${featureName}'. Valid values are: ${BedrockLogs.VALID_FEATURE_NAMES.join(', ')}`);
            }
        }
        this.featureName = featureName;
        this.stepCounter = 0;

        if (this.deliveryStreamName === null) {
            throw new Error("delivery_stream_name must be provided or set equals to 'local' example: delivery_stream_name='local'.");
        }

        if (this.deliveryStreamName === 'local') {
             this.firehoseClient=null;
        }
        else{
             this.firehoseClient = new AWS.Firehose();
        }

    }

    static findKeys(dictionary, key, path = []) {
        const results = [];

        if (typeof dictionary === 'object' && dictionary !== null) {
            if (Array.isArray(dictionary)) {
                dictionary.forEach((item, i) => {
                    const newPath = [...path, i];
                    results.push(...BedrockLogs.findKeys(item, key, newPath));
                });
            } else {
                Object.entries(dictionary).forEach(([k, v]) => {
                    const newPath = [...path, k];
                    if (k === key) {
                        results.push([newPath, v]);
                    } else {
                        results.push(...BedrockLogs.findKeys(v, key, newPath));
                    }
                });
            }
        }

        return results;
    }

    extractSessionId(logData) {
        
        /* Extracts the session ID from the log data. If the session ID is not available,
        it generates a new UUID for the run ID.*/

        let sessionIdPaths;
        if (this.featureName === "Agent") {
            sessionIdPaths = BedrockLogs.findKeys(logData, 'sessionId');
        } else {
            sessionIdPaths = BedrockLogs.findKeys(logData, 'sessionId');
        }

        if (sessionIdPaths.length > 0) {
            const [path, sessionId] = sessionIdPaths[0];
            return sessionId;
        } else {
            return uuidv4();
        }
    }
    
       
    handleAgentFeature(outputData, requestStartTime) {
        
        /* If feature being watched is 'Agent', this method will handle agent 
       specific tracing logging capabilities*/
       
        this.sessionId = null;
        let prevTraceTime = null;
        return outputData.map(data => {
            if (typeof data === 'object' && data !== null && 'trace' in data) {
                const trace = data.trace;
                if ('start_trace_time' in trace) {
                    //Check if 'start_trace_time' is defined correctly
                    if (typeof trace['start_trace_time'] !== 'number'){
                        throw new Error("The key 'start_trace_time' should be present and should be a time.time() object.");
                    }
                    //Calculate the latency between traces
                    if (prevTraceTime === null) {
                        trace['latency'] = trace['start_trace_time'] - requestStartTime;
                    } else {
                        trace['latency'] = trace['start_trace_time'] - prevTraceTime;
                    }

                    prevTraceTime = trace['start_trace_time'];
                    trace['step_number'] = this.stepCounter;
                    this.stepCounter += 1;
                    data['trace'] = trace;
                }
            } else if (Array.isArray(data)) {
                return data.map(item => {
                    //Check if 'start_trace_time' is defined correctly
                    if (typeof item === 'object' && item !== null && 'start_trace_time' in item) {
                        if (typeof item['start_trace_time'] !== 'number') {
                            throw new Error("The key 'start_trace_time' should be present and should be a time.time() object.");
                        }
                        //Calculate the latency between traces
                        if (prevTraceTime === null) {
                            item['latency'] = item['start_trace_time'] - requestStartTime;
                        } else {
                            item['latency'] = item['start_trace_time'] - prevTraceTime;
                        }

                        prevTraceTime = item['start_trace_time'];
                        item['step_number'] = this.stepCounter;
                        this.stepCounter += 1;
                    } else if (typeof item === 'object' && item !== null && 'trace' in item) {
                        const trace = item['trace'];
                        if ('start_trace_time' in trace) {
                            //Check if 'start_trace_time' is defined correctly
                            if (typeof trace['start_trace_time'] !== 'number') {
                                throw new Error("The key 'start_trace_time' should be present and should be a time.time() object.");
                            }
                            //Calculate the latency between traces
                            if (prevTraceTime === null) {
                                trace['latency'] = trace['start_trace_time'] - requestStartTime;
                            } else {
                                trace['latency'] = trace['start_trace_time'] - prevTraceTime;
                            }

                            prevTraceTime = trace['start_trace_time'];
                            trace['step_number'] = this.stepCounter;
                            this.stepCounter += 1;
                            //Update the 'trace' dictionary in the original item
                            item['trace'] = trace;
                        }
                    }
                    return item;
                });
            }
            return data;
        });
    }

       
    watch(inputs={}) {
        
        /* This method provides the decorator functionality that will be used to log 
       data within the watched function */
        
        var { captureInput = true, captureOutput = true, callType = 'LLM' } = inputs;
        let runId;
        return (func) => {
            return async (...args) => {
                
                //For Latency Calculation
                this.requestStartTime = performance.now();
                
                //Get the function name
                const functionName = func.name;
                
                //Capture input if requested
                const inputData = captureInput ? args : null;
                
                let inputLog = null
                if (inputData) {
                    inputLog = inputData[0];
                }
                
                //Generate observation_id
                const observationId = uuidv4();
                const obsTimestamp = new Date().toISOString();
                
                //Get the start time
                const startTime = performance.now();
                
            
                var outputData;
                let result;
                
                //Calls the function to be executed, the decorated function
                try {
                result = await func(...args);
                //console.log('results',result)
                //Capture output if requested
                outputData = captureOutput ? result : null;
                } 
                catch (error) {
                console.error('Error:', error);
                }
                
                // Get the end time
                const endTime = performance.now();
                
                //Calculate the duration (ms)
                const duration = endTime - startTime;
                
                //Begin Logging Time:
                const loggingStartTime = performance.now();
                
                let runId;

                if (this.featureName !== "Agent") {
                    this.stepCounter = 0;
                }
                
                //Handle the 'Agent' feature case
                if (this.featureName === "Agent") {
                    if (outputData !== null) {
                        outputData = this.handleAgentFeature(outputData, this.requestStartTime);
                        runId = this.extractSessionId(outputData);
                    }
                    else {
                        runId = this.extractSessionId(inputLog)
                    }
                } else {
                    //Extract the session ID from the log or generate a new one
                    runId = this.extractSessionId(inputLog);
                }
                
                //Prepare the metadata
                const metadata = {
                    experiment_id: this.experimentId,
                    run_id: runId,
                    observation_id: observationId,
                    obs_timestamp: obsTimestamp,
                    start_time: new Date(startTime).toISOString(),
                    end_time: new Date(endTime).toISOString(),
                    duration,
                    input_log: inputLog,
                    output_log: outputData,
                    call_type: callType || this.defaultCallType,
                };
                
                //Update the metadata with additional_metadata if provided
                const additionalMetadata = args[args.length - 1]?.additional_metadata || {};
                Object.assign(metadata, additionalMetadata);

                const inputDataVar = args[args.length - 1]?.user_prompt || {};
                Object.assign(metadata, inputDataVar);
                
                //Get the end time
                const loggingEndTime = performance.now();
                const loggingDuration = loggingEndTime - loggingStartTime;
                
                // logging duration is in milliseconds
                metadata['logging_duration'] = loggingDuration;
                
                //Send the metadata to Amazon Kinesis Data Firehose or return it locally for testing:
                if (this.deliveryStreamName ==='local') {
                    if (this.feedbackVariables){
                        console.log("Logs in local mode-with feedback:");
                        return [result,JSON.stringify(metadata),runId,observationId];
                    }
                    else{
                        console.log("Logs in local mode-without feedback:");
                        return [result,JSON.stringify(metadata)];
                    }
                } 
                
                //log to firehose
                else {
                    const firehoseResponse = this.firehoseClient.putRecord({
                        DeliveryStreamName: this.deliveryStreamName,
                        Record: {
                            Data: JSON.stringify(metadata)
                        }
                    }).promise();
                    if (this.feedbackVariables){
                        console.log("Logs in S3-with feedback:");
                        return [result,runId,observationId];
                    }
                    else{
                        console.log("Logs in S3-without feedback:");
                        return result;
                    }
                }
            };
        };
    }
}

export default BedrockLogs;