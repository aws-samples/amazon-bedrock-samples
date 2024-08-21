use aws_config::{meta::region::RegionProviderChain, BehaviorVersion};
use aws_lambda_events::apigw::ApiGatewayWebsocketProxyRequest;
use aws_sdk_apigatewaymanagement::{
    config::Builder, primitives::Blob as ApiGatewayBlob, Client as ApiGatewayManagementClient,
};
use aws_sdk_bedrockruntime::{
    operation::invoke_model_with_response_stream::InvokeModelWithResponseStreamOutput,
    primitives::Blob as BedrockBlob, types::ResponseStream, Client as BedrockClient,
};
use http::Uri;
use lambda_runtime::{service_fn, Error as LambdaError, LambdaEvent};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::sync::mpsc;

/// Required Amazon API Gateway response
#[derive(serde::Serialize)]
struct ApiGatewayResponse {
    #[serde(rename = "statusCode")]
    status_code: u16,
    body: String,
}

/// Response for each stream record sent from Amazon Bedrock
#[derive(Debug, Deserialize, Serialize)]
struct BedrockResponse {
    #[serde(rename = "type")]
    response_type: String,
    completion: String,
    stop_reason: Option<String>,
    stop: Option<Value>,
}

/// Bedrock story
#[derive(Debug, Deserialize)]
struct StoryRequest {
    #[serde(rename = "storyType")]
    story_type: String,
}

/// Main Lambda handler here...
async fn function_handler(
    event: LambdaEvent<ApiGatewayWebsocketProxyRequest>,
) -> Result<ApiGatewayResponse, LambdaError> {
    let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
    let config = aws_config::defaults(BehaviorVersion::latest())
        .region(region_provider)
        .load()
        .await;

    let bedrock_client = BedrockClient::new(&config);

    let connection_id = event
        .payload
        .request_context
        .connection_id
        .as_deref()
        .ok_or_else(|| LambdaError::from("Missing connection_id"))?;
    let domain_name = event
        .payload
        .request_context
        .domain_name
        .as_deref()
        .ok_or_else(|| LambdaError::from("Missing domain_name"))?;
    let stage = event
        .payload
        .request_context
        .stage
        .as_deref()
        .ok_or_else(|| LambdaError::from("Missing stage"))?;

    match event.payload.request_context.route_key.as_deref() {
        Some("$connect") => handle_connect(connection_id).await,
        Some("$disconnect") => handle_disconnect(connection_id).await,
        Some("$default") => {
            let endpoint = format!("https://{}/{}", domain_name, stage);
            let uri = endpoint.parse::<Uri>()?;
            let api_gateway_client = ApiGatewayManagementClient::from_conf(
                Builder::from(&config).endpoint_url(uri.to_string()).build(),
            );
            let request_body = event.payload.body;
            handle_default(
                bedrock_client,
                api_gateway_client,
                connection_id,
                request_body,
            )
            .await
        }
        Some(_) | None => Ok(ApiGatewayResponse {
            status_code: 400,
            body: "Unknown route".to_string(),
        }),
    }
}

/// Handle WebSocket connection
async fn handle_connect(connection_id: &str) -> Result<ApiGatewayResponse, LambdaError> {
    println!("New connection: {}", connection_id);
    Ok(ApiGatewayResponse {
        status_code: 200,
        body: "Connected...: $connect".to_string(),
    })
}

/// Handle WebSocket disconnect
async fn handle_disconnect(connection_id: &str) -> Result<ApiGatewayResponse, LambdaError> {
    println!("Disconnected: {}", connection_id);
    Ok(ApiGatewayResponse {
        status_code: 200,
        body: "Disconnected...: $disconnect".to_string(),
    })
}

/// Handle WebSocket default message
async fn handle_default(
    bedrock_client: BedrockClient,
    api_gateway_client: ApiGatewayManagementClient,
    connection_id: &str,
    request_body: Option<String>,
) -> Result<ApiGatewayResponse, LambdaError> {
    println!("Calling $default with connection_id [{}]", connection_id);

    // Parse the incoming JSON payload
    let story_request: StoryRequest = match request_body {
        Some(body_str) => serde_json::from_str(&body_str)
            .map_err(|e| LambdaError::from(format!("Failed to parse request body: {}", e)))?,
        None => return Err(LambdaError::from("Missing request body")),
    };

    // Construct the prompt based on the type of story to create
    let prompt = format!(
        "\n\nHuman: Tell me a very short story about: {}\n\nAssistant:",
        story_request.story_type
    );
    println!("Bedrock story prompt...: {}", prompt);

    // Create the Bedrock payload
    let payload = json!({
        "prompt": prompt,
        "max_tokens_to_sample": 300,
        "temperature": 0.7,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    });
    let body = BedrockBlob::new(serde_json::to_string(&payload)?);

    // Make the Bedrock request
    let bedrock_response = bedrock_client
        .invoke_model_with_response_stream()
        .model_id("anthropic.claude-v2")
        .content_type("application/json")
        .accept("application/json")
        .body(body)
        .send()
        .await?;

    // Start reading from Bedrock & writing the API GW
    bedrock_websocket_pipeline(
        bedrock_response,
        api_gateway_client,
        connection_id.to_string(),
    )
    .await?;

    Ok(ApiGatewayResponse {
        status_code: 200,
        body: "Message processed...: $default".to_string(),
    })
}

/// Start the Bedrock + Websocket threads
async fn bedrock_websocket_pipeline(
    response: InvokeModelWithResponseStreamOutput,
    api_gateway_client: ApiGatewayManagementClient,
    connection_id: String,
) -> Result<(), LambdaError> {
    let (sender, receiver) = mpsc::channel(100); // Adjust buffer size as needed

    let bedrock_task = tokio::spawn(async move { process_bedrock_stream(sender, response).await });

    let websocket_task = tokio::spawn(async move {
        send_to_websocket(receiver, api_gateway_client, connection_id).await
    });

    // Wait for both tasks to complete
    let (bedrock_result, websocket_result) = tokio::try_join!(bedrock_task, websocket_task)
        .map_err(|e| LambdaError::from(format!("Task join error: {}", e)))?;

    // Propagate errors from the tasks
    bedrock_result?;
    websocket_result?;

    Ok(())
}

/// Process the Bedrock stream
async fn process_bedrock_stream(
    sender: mpsc::Sender<BedrockResponse>,
    mut bedrock_response: InvokeModelWithResponseStreamOutput,
) -> Result<(), LambdaError> {
    println!("Processing Bedrock stream...");

    while let Some(event) = bedrock_response
        .body
        .recv()
        .await
        .map_err(LambdaError::from)?
    {
        match event {
            ResponseStream::Chunk(payload) => {
                if let Some(blob) = payload.bytes() {
                    let data = BedrockBlob::clone(blob).into_inner();
                    match serde_json::from_slice::<BedrockResponse>(&data) {
                        Ok(response) => {
                            if sender.send(response).await.is_err() {
                                eprintln!("Receiver dropped error");
                                return Err(LambdaError::from(
                                    "Receiver dropped, stopping Bedrock processing",
                                ));
                            }
                        }
                        Err(e) => {
                            eprintln!("Error deserializing response: {:?}", e);
                            return Err(LambdaError::from(e));
                        }
                    }
                }
            }
            other => {
                eprintln!("Unexpected event: {:?}", other);
                return Err(LambdaError::from("Unexpected event from Bedrock stream"));
            }
        }
    }

    println!("Bedrock stream processing complete...");
    Ok(())
}

/// Process incoming Bedrock messages and send to WebSocket
async fn send_to_websocket(
    mut reciever: mpsc::Receiver<BedrockResponse>,
    api_gateway_client: ApiGatewayManagementClient,
    connection_id: String,
) -> Result<(), LambdaError> {
    println!("Starting WebSocket sender...");

    while let Some(response) = reciever.recv().await {
        api_gateway_client
            .post_to_connection()
            .connection_id(connection_id.clone())
            .data(ApiGatewayBlob::new(
                serde_json::to_vec(&response).map_err(|e| LambdaError::from(e.to_string()))?,
            ))
            .send()
            .await
            .map_err(LambdaError::from)?;
    }

    println!("WebSocket sender complete...");
    Ok(())
}

/// Lambda Entry
#[tokio::main]
async fn main() -> Result<(), LambdaError> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .without_time()
        .init();

    lambda_runtime::run(service_fn(function_handler)).await
}
