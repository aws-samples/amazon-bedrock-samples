package com.example.app.utils;

import java.util.Iterator;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrock.BedrockClient;
import software.amazon.awssdk.services.bedrock.model.FoundationModelSummary;
import software.amazon.awssdk.services.bedrock.model.ListFoundationModelsRequest;
import software.amazon.awssdk.services.bedrock.model.ListFoundationModelsResponse;

public class Utils {

    public void listFoundationModels(String awsRegion){

       BedrockClient bedrockClient = BedrockClient.builder()
                                    .region(Region.US_EAST_1)
                                    .credentialsProvider(DefaultCredentialsProvider.create())
                                    .build();


       ListFoundationModelsResponse modelsResult = bedrockClient.listFoundationModels(ListFoundationModelsRequest.builder().build());

       Iterator<FoundationModelSummary> it = modelsResult.modelSummaries().iterator();

       System.out.println("Printing the list of available ModelIds and correspinding Arns::"+ "\n\n");
       
       while(it.hasNext()){

       FoundationModelSummary modelSummary =  it.next();

         System.out.println("Foundation Model Id   :: "  + modelSummary.modelId()+"\n" +
                            "Foundation Model Arn :: " + modelSummary.modelArn()+"\n\n");

       }

    }
    
}
