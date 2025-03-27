// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ecs from "aws-cdk-lib/aws-ecs";
import { Construct } from "constructs";

// Local Dependencies:
import {
  ILangfuseServiceSharedProps,
  LangfuseServiceBase,
} from "./service-base";

const LANGFUSE_WORKER_PORT = 3030;

interface ILangfuseWorkerServiceProps extends ILangfuseServiceSharedProps {
  /**
   * Source container image name for the worker
   *
   * @default 'langfuse/langfuse-worker'
   */
  imageName?: string;
}

/**
 * Construct for an ECS-based service to run Langfuse's asynchronous background workers
 */
export class LangfuseWorkerService extends LangfuseServiceBase {
  constructor(
    scope: Construct,
    id: string,
    props: ILangfuseWorkerServiceProps,
  ) {
    super(scope, id, {
      ...props,
      healthCheck: {
        command: [
          "CMD-SHELL",
          // >> to capture health check in task/service logs as described at:
          // https://docs.aws.amazon.com/AmazonECS/latest/developerguide/view-container-health.html
          `wget --no-verbose --tries=1 --spider http://localhost:${LANGFUSE_WORKER_PORT}/api/health >> /proc/1/fd/1 2>&1  || exit 1`,
        ],
        interval: cdk.Duration.minutes(2),
        retries: 3,
        startPeriod: cdk.Duration.minutes(4),
        timeout: cdk.Duration.seconds(60), // Worker can get busy and that's okay
      },
      imageName: props.imageName || "langfuse/langfuse-worker",
      portMappings: [
        {
          containerPort: LANGFUSE_WORKER_PORT,
          hostPort: LANGFUSE_WORKER_PORT,
          protocol: ecs.Protocol.TCP,
        },
      ],
      serviceName: "worker",
    });
  }
}
