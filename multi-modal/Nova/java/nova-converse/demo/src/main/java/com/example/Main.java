package com.example;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.core.exception.SdkClientException;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.*;

import java.util.Arrays;

public class Main {

    public static String converse(String s3Uri) throws Exception {
        var client = BedrockRuntimeClient.builder()
                .credentialsProvider(DefaultCredentialsProvider.create())
                .region(Region.US_EAST_1)
                .build();

        var modelId = "amazon.nova-lite-v1:0";

        // Create video content block
        var videoContent = ContentBlock.builder()
                .video(video -> video
                        .format("mp4")
                        .source(source -> source
                                .s3Location(s3 -> s3
                                        .uri(s3Uri)
                                        )))
                .build();

        // Create text content block
        var prompt = "What is the main idea of the video?";
        var textContent = ContentBlock.fromText(prompt);

        // Create message with both video and text content
        var message = Message.builder()
                .content(Arrays.asList(videoContent, textContent))
                .role(ConversationRole.USER)
                .build();

        try {
            ConverseResponse response = client.converse(request -> request
                    .modelId(modelId)
                    .messages(message)
                    .inferenceConfig(config -> config
                            .maxTokens(4096)
                            .temperature(0.5F)
                            .topP(0.9F)));

            var responseText = response.output().message().content().get(0).text();
            System.out.println(responseText);
            return responseText;

        } catch (SdkClientException e) {
            System.err.printf("ERROR: Can't invoke '%s'. Reason: %s", modelId, e.getMessage());
            throw new RuntimeException(e);
        }
    }

    public static void main(String[] args) {
        String s3Uri = "s3://bedrock-video-generation-us-east-1-pi8hu9/video-class/cb4198e065f64149b7ccdf7f9b78f1b9.mp4";
        //String bucketOwner = "767828766472";
        try {
            converse(s3Uri);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
