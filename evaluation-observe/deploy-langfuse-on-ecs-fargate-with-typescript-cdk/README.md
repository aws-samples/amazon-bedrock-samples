# Self-Host Langfuse on Amazon ECS with Fargate using TypeScript CDK

Langfuse is an Open Source LLM Engineering platform that helps teams collaboratively debug, analyze, and iterate on their LLM applications.

This repository demonstrates how to deploy a self-hosted Langfuse solution using AWS Fargate for Amazon ECS. It is designed for initial experimentation and is not suitable for production use. Additionally, it does not include all capabilities available in the Langfuse Enterprise Edition. For production-ready deployments, check out the [Langfuse offerings through AWS Marketplace](https://aws.amazon.com/marketplace/seller-profile?id=seller-nmyz7ju7oafxu).


## Architecture overview

This deployment involves multiple AWS services to host Langfuse components as described in their [official documentation on self-hosting](https://langfuse.com/self-hosting#architecture). In this sample, shown also in the architecture diagram below, we use:

1. [AWS Fargate for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) to host the required containers without the need to manage servers or clusters of Amazon EC2 instances
2. [Amazon RDS](https://aws.amazon.com/rds/postgresql/) for the Postgres OLTP store
3. [Amazon Elasticache](https://aws.amazon.com/elasticache/) for the Valkey cache
4. [Amazon EFS](https://aws.amazon.com/efs/) for durable managed storage to back the deployed [ClickHouse](https://clickhouse.com/docs/intro) OLAP system
5. [Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) for high-performance CDN and HTTPS connectivity to the deployed Langfuse service.

![](doc/CDK-Langfuse-Architecture.png "Architecture diagram showing LLM applications and web browsers connecting to Langfuse through the above described components")

### Request Flow Sequence:

1. **Client Request**: LLM applications and web browsers initiate requests through the Langfuse SDK or directly via the web interface. These requests are routed to Amazon CloudFront, which serves as the Content Delivery Network (CDN) to provide HTTPS termination, caching, and global distribution.
2. **Routing Through Application Load Balancer**: CloudFront forwards the requests to the Application Load Balancer (ALB) within the Virtual Private Cloud (VPC). The ALB ensures proper routing of traffic to the ECS cluster hosting Langfuse components.
3. **Processing in ECS Cluster**: The ECS cluster, powered by AWS Fargate, processes requests using two primary components:

    * Langfuse Web Server: Handles API endpoints and user-facing interactions.
    * Langfuse Worker: Processes background tasks such as event batching and analytics.

4. **Data Storage Operations**: Depending on the type of data being processed, requests interact with various storage systems:

    * Amazon RDS Aurora Postgres OLTP: Stores transactional data such as user configurations, API keys, and project metadata.
    * Amazon EFS-backed ClickHouse OLAP: Handles analytical workloads for high-volume trace and span data.
    * Amazon S3: Stores raw objects like logs or files uploaded during processing.

5. **Caching with ElastiCache**: The system utilizes Amazon ElastiCache (Valkey cache) for Redis-compatible caching to optimize performance by reducing database load and enabling faster access to frequently queried data.
6. **Response Delivery**: Once processing is complete, responses are sent back to clients through the same path, ensuring secure delivery via CloudFront. Metrics and logs generated during processing from ECS are also forwarded to Amazon CloudWatch for observability.

This flow ensures efficient handling of requests while leveraging AWS's managed services for scalability, reliability, and security.


## Deployment option 1: Quick start

If you don't have CDK development tooling set up already, and would just like to deploy the Langfuse architecture with the default settings - you can use the [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) template in [cfn_bootstrap.yml](./cfn_bootstrap.yml): Open the [CloudFormation Console](https://console.aws.amazon.com/cloudformation/home?#/stacks/create) in your target AWS Account and Region, click **Create stack**, and upload the template file.

This "bootstrap" stack sets up a CI project in [AWS CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html) which pulls the sample code and performs the below app CDK setup steps for you automatically in the Cloud - with no local development environment required. ⚠️ **Note** though, that the CodeBuild project is granted *broad permissions* to deploy all the sample's AWS resources on your behalf - so is not recommended for use in production environments as-is.


## After deployment: Getting started

You can find the URL to access your Langfuse UI from the `LangfuseUrl` "Output" of your stack in [CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html).

If you deployed with the default, recommended configuration (see [bin/demo.ts](bin/demo.ts)) using Amazon Cognito for authentication, you'll need to head on over to your created user pool in the [Amazon Cognito User Pools console](https://console.aws.amazon.com/cognito/v2/idp/user-pools) to set yourself up a username and password for logging in to Langfuse.

If you *disabled* Cognito during deployment, you can simply "Sign up" from your Langfuse URL.

> ⚠️ **Warning:** Allowing public open sign-up is not recommended! you could also consider re-deploying the `LangfuseDemo` construct with `langfuseEnvironment: {'AUTH_DISABLE_SIGNUP': 'true'}` to disable it, after creating your first admin user.



## Deployment option 2: Developer setup (Suggested workflow)

If you are comfortable with CDK deployment or want to customize the app, you'll need to set up your local development environment rather than using the quick-start template above.

### Prerequisites:

1. Docker or Finch

    This project requires a local container build environment. If your organization doesn't support [Docker Desktop](https://www.docker.com/products/docker-desktop/), you can instead install [Finch](https://runfinch.com/). If using Finch instead of Docker, remember to:

    - Initialise the VM with `finch vm start`, and
    - Tell CDK how to build containers, by running `export CDK_DOCKER=finch` (on MacOS/Linux), or `SET CDK_DOCKER=finch` (on Windows)

2.  NodeJS

    This project requires [NodeJS](https://nodejs.org/) v20+

3.  AWS CLI login

    To actually deploy the infrastructure to a target AWS Account (and possibly, even to synthesize a concrete template), you'll need to [configure your AWS CLI credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html). Note that whatever principal you log in to AWS with (User, Role, etc) will need the relevant *IAM Permissions* to deploy and manage all types of resources used by the sample - which is a broad set.

    You'll also want to set your target *AWS Region*. You can check your current active AWS Account by running `aws sts get-caller-identity`, and your selected region with `aws configure get region`.


### Development workflow

Once your development environment is set up, this sample works like a standard CDK app project.

First, install the project's dependencies:

```bash
npm install
```

Then, you can deploy it to AWS:

```bash
# Deploy or update all Stacks in the app:
# (Optionally specify --require-approval never to suppress approval prompts)
npx cdk deploy --all
```

To **delete** the deployed infrastructure when you're done exploring, and avoid ongoing charges:

> ⚠️ **Warning:** Running the below will irreversibly delete any data you've stored in your deployed Langfuse instance!

```bash
npx cdk destroy --all
```

**Other useful commands** for the project include:
- `npx cdk destroy` to delete the deployed infrastructure
- `npx cdk synth` to ["synthesize"](https://docs.aws.amazon.com/cdk/v2/guide/configure-synth.html) the CDK application to deployable CloudFormation template(s), without actually deploying
- `npx cdk list` to list all CDK stacks and their dependencies

Refer to the [CDK CLI commands guide](https://docs.aws.amazon.com/cdk/v2/guide/ref-cli-cmd.html) for a full reference


## License
This library is licensed under the MIT-0 License. See the LICENSE file.
