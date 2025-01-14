### ConverseSQLAgent: Building an intelligent text-to-SQL agent using Amazon Bedrock and Converse API. This is a Sample Code for a quick POC and the infrastructure can be adapted based on final implementation.

Authors: Ross Alas, Pavan Kumar, Parag Srivastava and Abdullah Siddiqui 

ConverseSQLAgent is a simple and powerful text-to-sql solution that can connect to
different databases and queries them all through natural language. It is built using
Amazon Bedrock, Converse API, and a custom agent implementation that enables it to
plan, execute, and learn as you use it.


### Manual Installation steps

1. You will need to deploy the Lambda using the deployment/lambda.zip 
2. Configure Lambda to connect to the VPC where your RDS database is
3. Configure the following VPC endpoints in the same VPC:
- Bedrock Runtime (com.amazonaws.<region>.bedrock-runtime)
- DynamoDB (com.amazonaws.<region>.dynamodb)
- Secrets Manager  (com.amazonaws.<region>.secretsmanager)
4. Ensure the Lambda execution role has permissions:
- Bedrock Converse and the Claude 3 Sonnet
- DynamoDB table for use with the agent
- Secrets Manager key to store the RDS credentials
5. Ensure Lambda has the following enviroment variables:
- DynamoDbMemoryTable (advtext2sql_memory_tb)
- BedrockModelId (anthropic.claude-3-sonnet-20240229-v1:0)
6. Ensure that Lambda/VPC endpoints/RDS security groups allow communication


### This section contains details on how to run the setup using CDK code written in Python.

### Prerequisites 

1. Ensure CDK is installed and [bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html) the environment as required to connect it to your AWS account. 
```
$ npm install -g aws-cdk
```

2. Check for existence of Python 3.11. 

```
python 3.11 --version
```

3. If the response is "python: command not found". Install Python 3.11 and pip for Python 3.11
```
sudo dnf install python3.11 -y
sudo dnf install python3.11-pip -y
```

### To run example

Clone the code to your working environment. Follow the steps as mentioned. 

1. Change your working directory to the downloaded folder. 
```
$ cd ConverseSqlAgent
```

2. Run the following Script to download the dependencies recuired by the lambda layer and creating a zip file to be utilized as a layer for the lambda code. 
```
cd ./src/layers
python3.11 -m venv create_layer
source create_layer/bin/activate
pip install -r requirements.txt
mkdir python
cp -r create_layer/lib python/
zip -r layer_content.zip python
deactivate
cd ../../
```

3. Once bak in the working directory of your code. Create a Python virtual environment
```
python3.11 -m venv .venv
```

4. Activate virtual environment

_On MacOS or Linux_
```
source .venv/bin/activate
```

_On Windows_
```
.venv\Scripts\activate.bat
```

5. Install the required dependencies.

```
pip install -r requirements.txt
```

6. Synthesize (`cdk synth`) or deploy (`cdk deploy`) the example

```
cdk deploy
```

### To dispose of the stack afterwards:

```
cdk destroy
```

7. Once the resources are built. Connect to the MySQL RDS instance and run the sample HR schema using the file "hr-schema-mysql.sql" from "sql" folder.

Ensure that you have the mysql agent installed and that the RDS MySQL instance security group allows inbound traffic on port 3306.

8. First, create the database schema. Retrieve the username, password and databse hostname values from Secrets Manager.

```
mysql -u <username> -p -h <database hostname> -P 3306 < ./sql/hr-schema-mysql.sql
```

9. Connect to database and check if the new HR database is created.

```
mysql -u <username> –p -h <database hostname> -P 3306
```

10. After connecting check the databases and the tables in the HR database.
```
show databases;
show tables;
```

11. You can test the lambda using the simple prompt. as given below. 

```
{
  "input_text": "Connect to the database hr using the secrets manager key <Database key> and get me how many employees are there in each department in each region?"
}
```
