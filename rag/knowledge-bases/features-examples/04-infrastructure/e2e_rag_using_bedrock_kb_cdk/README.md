
# Deploy e2e RAG solution (using Knowledgebases for Amazon Bedrock) via CDK
<mark>By no means this deployment is production-ready deployment. Please adjust the IAM polies and permissions as per your organization policy)</mark>

This is a complete setup for automatic deployment of end-to-end RAG workflow using Knowledge Bases for Amazon Bedrock. 
Following resources will get created and deployed:
- IAM role
- Open Search Serverless Collection and Index
- Set up Data Source (DS) and Knowledge Base (KB)

## Deployment steps

```
    -  git clone https://github.com/aws-samples/amazon-bedrock-samples.git
    
    -  cd cd knowledge-bases/features-examples/04-infrastructure/e2e_rag_using_bedrock_kb_cdk

```
This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually. 

__NOTE:__ *This project assumes you have python3.8 installed.
If you want to use a later version, you may have to make changes to the dependency versions
in requirements.txt.*



To manually create a virtualenv on MacOS and Linux:

```
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
.venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
pip install -r requirements.txt
```

### IMPORTANT : Update Config file 
**Open `config.py` and adjust the below parmaters as per your application configuration**:
- ACCOUNT_ID
- ACCOUNT_REGION
- RAG_PROJ_NAME
- CHUNKING_STRATEGY
- MAX_TOKENS
- OVERLAP_PERCENTAGE
- S3_BUCKET_NAME


**Save it!**

At this point you can now prepare the code zip and synthesize the CloudFormation template for this code. 

On your terminal, export your AWS credentials for a role/user in ACCOUNT_ID. The role needs to have all permissions necessary to do the operations in this repository:
```
export AWS_REGION="<region>" # Same region as ACCOUNT_REGION above
export AWS_ACCESS_KEY_ID="<access-key>" # Set to the access key of your role/user
export AWS_SECRET_ACCESS_KEY="<secret-key>" # Set to the secret key of your role/user
```

To create the dependency run:
```
./prepare.sh
```

When deploying for the *first time*, run:
```
cdk bootstrap
```


```
cdk synth
```

As this deployment contains multiple stacks, you have to deploy them in a specific sequence. Deploy the stack(s) in following order

```
cdk deploy KbRoleStack 
```

```
cdk deploy OpenSearchServerlessInfraStack 
```

```
cdk deploy KbInfraStack 
```

To Destroy the stack(s)

```
cdk destroy --all 
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
