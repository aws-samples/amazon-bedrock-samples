package main.java.com.example.app;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.nio.charset.Charset;
import java.time.temporal.ChronoUnit;
import java.time.Duration;

import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.http.apache.ApacheHttpClient;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClientBuilder;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;


public class App {
    public static void main(String[] args) {
        // read prompt from txt file
        String filePath = "./example-payload.txt";
        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            StringBuilder content = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                content.append(line).append("\n"); // Append each line to the content
            }
            String BEDROCK_JSON_BODY = content.toString();
            BEDROCK_JSON_BODY = BEDROCK_JSON_BODY.substring(0, BEDROCK_JSON_BODY.length() - 1);
            
            // send prompt to bedrock
            String awsRegion = "us-east-1";
            BedrockRuntimeClient bedrockClient = BedrockRuntimeClient.builder()
                .region(Region.of(awsRegion))
                .httpClient(
                    ApacheHttpClient.builder()
                    .socketTimeout(Duration.of(2, ChronoUnit.MINUTES))
                    .build())
                    .build();
            InvokeModelResponse invokeModel = bedrockClient
                .invokeModel(InvokeModelRequest.builder()
                .modelId("anthropic.claude-v2")
                .body(SdkBytes.fromString(BEDROCK_JSON_BODY, Charset.defaultCharset()))
                .build());
            System.out.println(invokeModel.body().asUtf8String());
        }
        catch (IOException e) {
            e.printStackTrace();
        }
    }
}