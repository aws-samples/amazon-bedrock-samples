
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
    
    -  cd knowledge-bases/03-infra/e2e-rag-deployment-using-bedrock-kb-cdk

```
This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.



To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

<b>Now open config.py and adjust the parmaters as per your application configuration, and save it.</b>

At this point you can now synthesize the CloudFormation template for this code. 

```
$ cdk synth
```

As this deployment contains multiple stacks, you have to deploy them in a specific sequence. Deploy the stack(s) in following order

```
$ cdk deploy KbRoleStack 
```

```
$ cdk deploy OpenSearchServerlessInfraStack 
```

```
$ cdk deploy KbInfraStack 
```

To Destroy the stack(s)

```
$ cdk destroy --all 
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
