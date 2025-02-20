# Scenario 2 - Role-Based access to PII data during retrieval

![Scenario1 data redaction pipeline](../images/scenario_2_inference_flow.png)

## Architecture break-down

* Authentication Flow (Steps 1-3)
  * User initiates request by obtaining authorization token from Cognito User Pool  
  * API call is made with authentication token to API Gateway
  * API Gateway forwards claims to AWS Lambda for processing
* Access Control Validation (Step 4)
  * System checks for admin access privileges
  * Request is routed to one of two paths based on user role:
    * Admin path: Uses admin-specific guardrails
    * Non-admin path: Implements stricter PII controls
* Knowledge Base Processing (Steps 5-8)
  * Query processing through Bedrock Knowledge Base includes:
    * Embedding generation using Amazon Titan
    * Similarity search via OpenSearch Vector DB
    * Application of metadata filters based on user role
  * Two distinct guardrail configurations process requests:
    * Admin Guardrail: Minimal PII restrictions
    * Non-Admin Guardrail: Enhanced PII protection
* Response Generation (Steps 9-10)
  * Bedrock LLM generates appropriate response
  * Guardrail validation check:
    * If blocked: Returns "Sorry! Cannot Respond" message
    * If passed: Returns role-appropriate response
      * Admin users receive full information
      * Non-admin users receive PII-masked information

### Usage

Step 1:

set environment variables and run bootsrap. Replace `ACCOUNT_ID` with your AWS ACCOUNT_ID.

```shell
[ "${PWD##*/}" = "scenario_1" ] && cd ..
cd scenario_2/cdk

export CDK_DEFAULT_ACCOUNT=ACCOUNT_ID && export CDK_DEFAULT_REGION=us-west-2 && \
  export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
```

At this point you can now synthesize the CloudFormation template for this code.

>**NOTE:** Before running the below command ensure docker desktop is running.

```shell
cdk bootstrap && cdk synth && cdk deploy
```

wait for the deployment to complete.

Step 2:

Execute the run_app.sh script under Scenario_2 folder

```shell
cd ..
chmod +x run_app.sh
./run_app.sh
```

This script will prompt you to enter a new password for the test logins.
Once the passwords are reset, it will upload test data to S3, sync the KnowledgeBase.

After the script completes it should automatically launch the streamlit app at <http://localhost:8501/>

* Login using `jane@example.com` or `john@example.com` with reset password earlier.
* From the sidebar, select a model from the drop-down.
* Optionally, set model params like `temperature` and `top_p` values.
* Ask questions based on your data files in [data](../data/) folder.

Here are a few sample questions:

* List all patients with Obesity as Symptom and the recommended medications
* List all patients under Institution Flores Group Medical Center
* Which patients are currently taking Furosemide and Atorvastatin medications
* Generate a list of all patient names and a summary of their symptoms

>**NOTE:** The above questions are just for reference your datafiles may or may not contain information on the questions. Check your datafiles in [data](../data/) folder.

### Cleanup (Scenario 2)

```shell
cd cdk
cdk destroy
```
