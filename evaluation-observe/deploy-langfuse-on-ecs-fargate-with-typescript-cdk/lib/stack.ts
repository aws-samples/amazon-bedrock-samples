import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

// Local Dependencies:
import { LangfuseDeployment, VpcInfra } from "./langfuse";

export class LangfuseDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const tags = [new cdk.Tag("project", "langfuse-demo")];

    const vpcInfra = new VpcInfra(this, "VpcInfra", { tags });

    // The code that defines your stack goes here
    const langfuse = new LangfuseDeployment(this, "Langfuse", {
      tags,
      vpc: vpcInfra.vpc,
    });

    new cdk.CfnOutput(this, "LangfuseUrl", {
      value: langfuse.url,
    });
  }
}
