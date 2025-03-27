// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as ecrDeploy from "cdk-ecr-deployment";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface IECRRepoAndDockerImageProps {
  /**
   * Name of the pre-existing Docker image to stage, including tag
   *
   * e.g. 'clickhouse:25.1' or 'langfuse/langfuse:latest'
   */
  dockerImageName: string;
  /**
   * Tag to give the *staged* image in ECR, e.g. 'latest' or '1.0.0'
   *
   * @default 'latest'
   */
  ecrImageTag?: string;
  /**
   * Name for the ECR image repository.
   *
   * The repository name must start with a letter and can only contain lowercase letters, numbers,
   * hyphens, underscores, and forward slashes. If you specify a name, you cannot perform updates
   * that require replacement of this resource. You can perform updates that require no or some
   * interruption. If you must replace the resource, specify a new name.
   *
   * @default undefined Automatically generated name.
   */
  repositoryName?: string;
  /**
   * AWS Tags to apply to created image registry
   */
  tags?: cdk.Tag[];
}

/**
 * Construct to create an ECR repository with sensible settings and stage a Docker image to it
 */
export class ECRRepoAndDockerImage extends Construct {
  public readonly repository: ecr.Repository;
  public readonly deployment: ecrDeploy.ECRDeployment;
  public readonly imageTag: string;

  constructor(
    scope: Construct,
    id: string,
    props: IECRRepoAndDockerImageProps,
  ) {
    super(scope, id);

    // Create the ECR repository:
    this.repository = new ecr.Repository(this, "Repo", {
      emptyOnDelete: true,
      encryption: ecr.RepositoryEncryption.AES_256,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      repositoryName: props.repositoryName,
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.repository).add(tag.key, tag.value),
      );
    }

    // Automatically clean up old or un-tagged images:
    this.repository.addLifecycleRule({
      maxImageAge: cdk.Duration.days(7),
      rulePriority: 1,
      tagStatus: ecr.TagStatus.UNTAGGED,
    });
    this.repository.addLifecycleRule({
      maxImageCount: 3,
      rulePriority: 2,
      tagStatus: ecr.TagStatus.ANY,
    });

    // Add the target image version(s):
    this.imageTag = props.ecrImageTag || "latest";
    this.deployment = new ecrDeploy.ECRDeployment(this, "Deployment", {
      src: new ecrDeploy.DockerImageName(props.dockerImageName),
      dest: new ecrDeploy.DockerImageName(
        this.repository.repositoryUriForTagOrDigest(this.imageTag),
      ),
    });

    const stack = cdk.Stack.of(this);
    NagSuppressions.addResourceSuppressionsByPath(
      stack,
      `${stack.node.path}/Custom::CDKECRDeploymentbd07c930edb94112a20f03f096f53666512MiB/ServiceRole/Resource`,
      [
        {
          id: "AwsSolutions-IAM4",
          reason:
            "Can't control managed policies within ECRDeployment resource",
        },
      ],
    );
    NagSuppressions.addResourceSuppressionsByPath(
      stack,
      `${stack.node.path}/Custom::CDKECRDeploymentbd07c930edb94112a20f03f096f53666512MiB/ServiceRole/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason:
            "Can't control wildcard policies within ECRDeployment resource",
        },
      ],
    );
  }
}
