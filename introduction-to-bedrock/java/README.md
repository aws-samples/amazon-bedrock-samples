# Java Bedrock REST Api Samples

This repository contains sample of how you can call `invokeModel` REST API and sign it with AWSSigV4 for Amazon Bedrock using Java programming language. The example uses Meta LLama 2 model but you can substitute it with any currently available model isd found on [AWS website](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids-arns.html).

## Contents

- [Run invokeModel API with Java](./my-app/src/main/java/com/mycompany/app/App.java) - Call invokeModel Amazon Bedrock REST API and sing it with AWSSigV4 using Java programming language

## Getting Started

To get started with the samples, follow these steps:

1. Clone the repository: `git clone https://github.com/aws-samples/amazon-bedrock-samples.git`
2. Navigate to the `introduction-to-bedrock/java/src/my-app` folder: `cd introduction-to-bedrock/java/src/my-app`
3. Open the `App.java` file in your preferred Java IDE.
4. Make sure you have your AWS credentials stored in the `credentials` file on your local machine.
5. Make sure you have Java and Maven installed on your machine.
6. Build and run the application. To do that you can run `mvn clean compile && mvn exec:java -Dexec.mainClass="com.mycompany.app.App" -e`

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.


