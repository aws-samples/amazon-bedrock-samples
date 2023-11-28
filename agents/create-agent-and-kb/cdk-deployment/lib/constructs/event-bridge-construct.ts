import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface EventBridgeProps extends cdk.StackProps {
  readonly createKbLambda: cdk.aws_lambda.Function;
}

const defaultProps: Partial<EventBridgeProps> = {};

export class EventBridgeConstruct extends Construct {
  public eventBusArn: string;

  constructor(scope: Construct, name: string, props: EventBridgeProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const eventBus = new cdk.aws_events.EventBus(this, "BedrockKbEventBus", {
      eventBusName: "BedrockKbEventBus"
    });

    const eventRule = new cdk.aws_events.Rule(this, "CreateKbEventRule", {
      ruleName: "CreateKbEventRule",
      description: "Rule to invoke Lambda function that creates KB from event sent by agent through another Lambda.",
      eventBus: eventBus,
      eventPattern: {
        source: ["create-kb.event"]
      },
      targets: [
        new cdk.aws_events_targets.LambdaFunction(props.createKbLambda)
      ]
    });

    this.eventBusArn = eventBus.eventBusArn;
  }
}