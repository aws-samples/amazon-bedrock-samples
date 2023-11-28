# AWS CloudFormation Deployment

The following tutorial assumes that you have an AWS account and have **Administrator Access** role associated with the current user to deploy the CloudFormation Stack.

# Installation:

1. Create S3 bucket and note its name.
2. Download [this](./assets/) folder and upload it to the S3 bucket that you just created. It is important that you upload the folder to S3 bucket as it is (root folder should be ``assets``), i.e. if your S3 bucket name is ``my-bucket-name`` then you should upload ``assets`` folder so the full path looks like ``my-bucket-name/assets``.

![Root S3 view](screenshots/s3-bucket/s3-root-view.png)

![Assets folder S3 view](screenshots/s3-bucket/s3-assets-view.png)

3. Download [this](cfn-template.yml) CloudFormation template.
4. [Navigate](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#) to the AWS CloudFormation console. You can also change your region to ``us-east-1`` if desired.
5. Click ``Create stack`` at the top right and select ``With new resources (standard)`` from the dropdown menu. 

![Create Stack 1](screenshots/cloudformation/create-stack-1.png)

6. Click ``Upload a template file`` and select the CloudFormation template that you downloaded in step 3. Click ``Next``.

![Create Stack 2](screenshots/cloudformation/create-stack-2.png)

7. Put a stack name and an agent name that you want your agent to have. **Keep your agent name length under 20 characters**. 
Provide S3 bucket name that you created in step 1. Click ``Next`` on the current page as well as the next page.

![Create Stack 3](screenshots/cloudformation/create-stack-3.png)

8. Scroll all the way down to the bottom page, tick in the acknowledge box and click ``Submit``.

![Create Stack 4](screenshots/cloudformation/create-stack-4.png)

# After intallation

A few steps to be completed after you deployed the infrastructure.

1. In the ``Outputs`` tab note ``S3BucketNameForNewAgentArtifacts`` and ``S3BucketNameForKnowledgeBaseDataSource`` values. ``S3BucketNameForNewAgentArtifacts`` value will contain S3 bucket name that you would need to use for the first prompt. ``S3BucketNameForKnowledgeBaseDataSource`` value will contain S3 bucket name that you will need to use in the second prompt. It will look like this:

<div align="center">
<img src="screenshots/cfn-outputs.png" />
</div>

2. In the console navigate to [Amazon Bedrock Agents](https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/agents). Select agent with the name that you provided. If you did not provide a name, the defaul name will be ``cfn-agent-kb``. In agent overview panel select ``Edit``:

<div align="center">
<img src="screenshots/create-and-test-alias/edit-user-input-1.png" />
</div>

3. Click ``Yes`` in ``User input`` panel. In the bottom right click ``Save``.

<div align="center">
<img src="screenshots/create-and-test-alias/edit-user-input-2.png" />
</div>

4. In the agent overview click ``Create Alias``.

<div align="center">
<img src="screenshots/create-and-test-alias/create-alias-1.png" />
</div>

5. Give your alias a name and click ``Create Alias``.

<div align="center">
<img src="screenshots/create-and-test-alias/create-alias-2.png" />
</div>

6. On the right side click ``Prepare``. This will "update" your agent's state.

<div align="center">
<img src="screenshots/create-and-test-alias/prepare-button.png" />
</div>

7. After agent is prepared click on the "expand" button in the top right.

<div align="center">
<img src="screenshots/create-and-test-alias/test-alias-1.png" />
</div>

8. Make sure you select the alias' name that you just created in the top dropdown menu. After that you can interacting with your agent.

<div align="center">
<img src="screenshots/create-and-test-alias/test-alias-2.png" />
</div>

# Prompt 1 example (initial prompt):

Feel free to experiment with the propmt. However, results might be unpredictable.

```
Give me a new agent called hello-world. Save the artifacts in my S3 bucket, named 'agent-452-artifacts-bucket'. 
The agent should have one action called hello that takes no inputs and gives back a string with the value 'hello world!'. 
Use this instruction for the new agent: 'You return Hello World whenever user asks you to call the function'.
```

# Prompt 2 example (after agent was created):

Feel free to experiment with the propmt. However, results might be unpredictable.

```
Create and associate to my agent new knowledge base. 
Use 'agent-452-knowledgebase-bucket' S3 bucket for it.
```

# How to delete the infrastructe

To delete the resources simply delete the CloudFormation stack. If you created a new agent and a knowledge base, make sure you remove OpenSearch Collection, new agent and a Knowledge Base associated to it in the console to stop incurring any charges associated with these services.