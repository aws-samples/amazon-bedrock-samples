# Connecting to Amazon Bedrock with the AWS Java SDK

This directory contains a simple maven project for how to interact with Amazon Bedrock though the Java SDK.

## Prerequisites

* Install Java (17.0.8 used in this example)
* Install Maven (3.9.4 used in this example)
* Authenticate to an AWS IAM role which has the correct permissions to invoke Amazon Bedrock models (This example uses Claude V2 from anthropic)

## How to Run

Inside the `my-app` directory, run these two maven commands. The first packages your code and the second executes the code.

```
mvn clean package
mvn exec:java -Dexec.mainClass="main.java.com.example.app.App"
```

This will execute the prompt stored in the `my-app/example-payload.txt` file. Feel free change this prompt to whatever you desire! Just make sure to correctly format the prompt and associated variables as per [this documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html).
