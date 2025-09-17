package org.example;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.core.document.Document;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.*;

import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.io.IOException;

public class ConverseMessage {
    public static void main(String[] args) throws IOException {
        BedrockRuntimeClient client = BedrockRuntimeClient.builder()
                .credentialsProvider(DefaultCredentialsProvider.create())
                .region(Region.US_EAST_1)
                .build();

        String modelId = "us.anthropic.claude-3-haiku-20240307-v1:0";  // Cross-region inference profile
        String inputText = "What's the weather like in San Francisco?";

        // Create tools that require chaining
        List<Tool> tools = createChainedTools();
        ToolConfiguration toolConfig = ToolConfiguration.builder()
                .tools(tools)
                .build();

        // Create system prompt using Anthropic best practices with XML tags
        List<SystemContentBlock> systemPrompt = List.of(
                SystemContentBlock.fromText(
                        "You are a helpful weather assistant that provides accurate, current weather information.\n\n" +

                                "<role>\n" +
                                "You help users get weather information by using the available tools in the correct sequence. " +
                                "Always be friendly, concise, and accurate.\n" +
                                "</role>\n\n" +

                                "<tool_usage_guidelines>\n" +
                                "- When a user asks for weather in a location, you MUST first use geocode_location to get coordinates\n" +
                                "- Then use get_timezone to get the proper timezone for that location\n" +
                                "- Finally use get_weather with the coordinates and timezone to get current conditions\n" +
                                "- Always follow this sequence - never skip steps\n" +
                                "</tool_usage_guidelines>\n\n" +

                                "<response_format>\n" +
                                "- Provide temperature, conditions, and any other relevant details\n" +
                                "- Include the local time when presenting weather information\n" +
                                "- Be conversational but informative\n" +
                                "- If you encounter any errors, explain what went wrong clearly\n" +
                                "</response_format>\n\n" +

                                "<important>\n" +
                                "- Only use the tools available to you\n" +
                                "- Don't make up weather information - always use the tool results\n" +
                                "- If a location cannot be found, let the user know and ask for clarification\n" +
                                "</important>"
                )
        );

        // Start the conversation loop
        List<Message> messages = new ArrayList<>();
        messages.add(Message.builder()
                .content(ContentBlock.fromText(inputText))
                .role(ConversationRole.USER)
                .build());

        // Create inference configuration with hyperparameters
        InferenceConfiguration inferenceConfig = InferenceConfiguration.builder()
                .temperature(0.3f)          // Lower temp for more consistent tool usage
                .topP(0.9f)
                .maxTokens(2000)
                .stopSequences(List.of("</final_answer>")) // Example stop sequences usage
                .build();

        runConversationLoop(client, modelId, messages, toolConfig, systemPrompt, inferenceConfig);
    }

    private static void runConversationLoop(BedrockRuntimeClient client, String modelId,
                                            List<Message> messages, ToolConfiguration toolConfig,
                                            List<SystemContentBlock> systemPrompt,
                                            InferenceConfiguration inferenceConfig) {
        int maxIterations = 8;
        int iteration = 0;

        while (iteration < maxIterations) {
            iteration++;
            System.out.println("\n=== ITERATION " + iteration + " ===");

            try {
                ConverseResponse response = client.converse(
                        request -> request
                                .modelId(modelId)
                                .messages(messages)
                                .system(systemPrompt)
                                .toolConfig(toolConfig)
                                .inferenceConfig(inferenceConfig)
                );

                System.out.println("Stop reason: " + response.stopReason());

                // Add the assistant's response to conversation
                messages.add(response.output().message());

                if (response.stopReason() == StopReason.TOOL_USE) {
                    handleToolUse(response, messages);
                } else if (response.stopReason() == StopReason.END_TURN) {
                    System.out.println("\n🏁 FINAL ANSWER:");
                    System.out.println(response.output().message().content().get(0).text());
                    System.out.println("\nTotal tokens: " + response.usage().totalTokens());
                    break;
                } else {
                    System.out.println("Unexpected stop reason: " + response.stopReason());
                    break;
                }

            } catch (Exception e) {
                System.err.println("Error in iteration " + iteration + ": " + e.getMessage());
                break;
            }
        }

        if (iteration >= maxIterations) {
            System.out.println("⚠️  Reached maximum iterations");
        }

        System.out.println("\nConversation had " + messages.size() + " total messages");
    }

    private static void handleToolUse(ConverseResponse response, List<Message> messages) {
        Message assistantMessage = response.output().message();

        for (ContentBlock block : assistantMessage.content()) {
            if (block.toolUse() != null) {
                ToolUseBlock toolUse = block.toolUse();
                System.out.println("🔧 Tool: " + toolUse.name());
                System.out.println("   Input: " + toolUse.input());

                // Simulate realistic tool execution
                String toolResult = executeToolRealistic(toolUse);
                System.out.println("   Result: " + toolResult);

                // Add tool result back to conversation
                messages.add(Message.builder()
                        .content(ContentBlock.fromToolResult(ToolResultBlock.builder()
                                .toolUseId(toolUse.toolUseId())
                                .content(ToolResultContentBlock.fromText(toolResult))
                                .build()))
                        .role(ConversationRole.USER)
                        .build());
            }
        }
    }

    private static String executeToolRealistic(ToolUseBlock toolUse) {
        Document input = toolUse.input();
        Map<String, Document> params = input.asMap();

        switch (toolUse.name()) {
            case "geocode_location":
                String location = params.get("location").asString();
                if (location.toLowerCase().contains("san francisco")) {
                    return "{\"latitude\": 37.7749, \"longitude\": -122.4194, \"city\": \"San Francisco\", \"state\": \"California\", \"country\": \"USA\"}";
                } else if (location.toLowerCase().contains("new york")) {
                    return "{\"latitude\": 40.7128, \"longitude\": -74.0060, \"city\": \"New York\", \"state\": \"New York\", \"country\": \"USA\"}";
                } else {
                    return "{\"latitude\": 0.0, \"longitude\": 0.0, \"city\": \"Unknown\", \"error\": \"Location not found\"}";
                }

            case "get_timezone":
                double lat = params.get("latitude").asNumber().doubleValue();
                double lon = params.get("longitude").asNumber().doubleValue();
                // SF coordinates
                if (Math.abs(lat - 37.7749) < 1 && Math.abs(lon + 122.4194) < 1) {
                    return "{\"timezone\": \"America/Los_Angeles\", \"offset\": \"-08:00\", \"dst\": false}";
                }
                return "{\"timezone\": \"UTC\", \"offset\": \"+00:00\"}";

            case "get_weather":
                lat = params.get("latitude").asNumber().doubleValue();
                lon = params.get("longitude").asNumber().doubleValue();
                String timezone = params.containsKey("timezone") ? params.get("timezone").asString() : "UTC";

                return String.format("{\"temperature\": 68, \"conditions\": \"Partly cloudy\", " +
                        "\"humidity\": 65, \"wind_speed\": 12, \"location\": \"%.4f, %.4f\", " +
                        "\"local_time\": \"2:30 PM %s\", \"feels_like\": 70}", lat, lon, timezone);

            default:
                return "{\"result\": \"Tool executed successfully\"}";
        }
    }

    private static List<Tool> createChainedTools() {
        List<Tool> tools = new ArrayList<>();

        // Step 1: Convert location name to coordinates
        tools.add(Tool.builder()
                .toolSpec(ToolSpecification.builder()
                        .name("geocode_location")
                        .description("Convert a location name (like 'San Francisco' or 'New York') to latitude/longitude coordinates")
                        .inputSchema(ToolInputSchema.builder()
                                .json(Document.fromMap(Map.of(
                                        "type", Document.fromString("object"),
                                        "properties", Document.fromMap(Map.of(
                                                "location", Document.fromMap(Map.of(
                                                        "type", Document.fromString("string"),
                                                        "description", Document.fromString("The city or location name")
                                                ))
                                        )),
                                        "required", Document.fromList(List.of(Document.fromString("location")))
                                )))
                                .build())
                        .build())
                .build());

        // Step 2: Get timezone for coordinates
        tools.add(Tool.builder()
                .toolSpec(ToolSpecification.builder()
                        .name("get_timezone")
                        .description("Get the timezone for specific latitude/longitude coordinates")
                        .inputSchema(ToolInputSchema.builder()
                                .json(Document.fromMap(Map.of(
                                        "type", Document.fromString("object"),
                                        "properties", Document.fromMap(Map.of(
                                                "latitude", Document.fromMap(Map.of(
                                                        "type", Document.fromString("number")
                                                )),
                                                "longitude", Document.fromMap(Map.of(
                                                        "type", Document.fromString("number")
                                                ))
                                        )),
                                        "required", Document.fromList(List.of(
                                                Document.fromString("latitude"),
                                                Document.fromString("longitude")
                                        ))
                                )))
                                .build())
                        .build())
                .build());

        // Step 3: Get weather using coordinates and timezone
        tools.add(Tool.builder()
                .toolSpec(ToolSpecification.builder()
                        .name("get_weather")
                        .description("Get current weather conditions for specific coordinates with timezone context")
                        .inputSchema(ToolInputSchema.builder()
                                .json(Document.fromMap(Map.of(
                                        "type", Document.fromString("object"),
                                        "properties", Document.fromMap(Map.of(
                                                "latitude", Document.fromMap(Map.of(
                                                        "type", Document.fromString("number")
                                                )),
                                                "longitude", Document.fromMap(Map.of(
                                                        "type", Document.fromString("number")
                                                )),
                                                "timezone", Document.fromMap(Map.of(
                                                        "type", Document.fromString("string"),
                                                        "description", Document.fromString("Timezone for local time context")
                                                ))
                                        )),
                                        "required", Document.fromList(List.of(
                                                Document.fromString("latitude"),
                                                Document.fromString("longitude")
                                        ))
                                )))
                                .build())
                        .build())
                .build());

        return tools;
    }
}