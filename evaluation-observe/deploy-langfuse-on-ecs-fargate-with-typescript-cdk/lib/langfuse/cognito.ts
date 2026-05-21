// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// NodeJS Built-Ins:
import * as crypto from "crypto";

// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

/**
 * Convenience construct for setting up a simple Cognito user pool and domain
 *
 * This is intended for basic setup only and does not enforce full best-practices for security with
 * Cognito. You probably don't want to add configuration props to this - but use the underlying
 * UserPool and UserPoolDomain constructs directly instead.
 */
export class BasicCognitoUserPoolWithDomain extends Construct {
  /**
   * Secret containing 'clientId', 'clientSecret', and 'issuer' values for your app
   */
  public readonly userPool: cognito.UserPool;
  /**
   * URL to access your Cognito User Pool's domain.
   */
  public readonly cognitoDomainUrl: string;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "UserPool", {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      autoVerify: {
        email: true,
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
        username: true,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    NagSuppressions.addResourceSuppressions(this.userPool, [
      { id: "AwsSolutions-COG2", reason: "MFA is not required for this demo" },
    ]);
    NagSuppressions.addResourceSuppressions(this.userPool, [
      {
        id: "AwsSolutions-COG3",
        reason: "AdvancedSecurityMode is not required for this demo",
      },
    ]);

    const domain = new cognito.UserPoolDomain(this, "Domain", {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: generateUniqueDomainName(this, {
          prefix: "langfuse-demo",
        }),
      },
    });
    this.cognitoDomainUrl = domain.baseUrl();
  }
}

export interface ILangfuseCognitoClientOptions {
  /**
   * Base URL of your Langfuse deployment - e.g. 'https://...cloudfront.net'
   */
  readonly baseUrl: string;
  /**
   * Customize the OAuth scopes that are allowed to be shared with this client
   * @default '[aws_cognito.OAuthScope.EMAIL, aws_cognito.OAuthScope.PROFILE]'
   */
  readonly scopes?: cognito.OAuthScope[];
}

/**
 * Add a 'client' to a Cognito user pool, configured for use with Langfuse
 */
export function addLangfuseCognitoClient(
  userPool: cognito.UserPool,
  id: string,
  options: ILangfuseCognitoClientOptions,
): cognito.UserPoolClient {
  return userPool.addClient(id, {
    generateSecret: true,
    oAuth: {
      callbackUrls: [options.baseUrl.concat("/api/auth/callback/cognito")],
      logoutUrls: [options.baseUrl.concat("/auth/sign-in")],
      scopes: options.scopes || [
        cognito.OAuthScope.EMAIL,
        cognito.OAuthScope.PROFILE,
      ],
      flows: {
        authorizationCodeGrant: true,
        implicitCodeGrant: true,
      },
    },
    supportedIdentityProviders: [
      cognito.UserPoolClientIdentityProvider.COGNITO,
    ],
  });
}

export interface ICognitoOAuthSecretProps {
  /**
   * Cognito user pool which must have been created with with `userPoolClientSecret` prop set true
   */
  userPool: cognito.IUserPool;
  /**
   * Cognito user pool 'client' for this application to connect as
   */
  client: cognito.IUserPoolClient;
}

/**
 * Construct for a secret with 'clientId', 'clientSecret', and 'issuer' from Cognito
 *
 * This secret includes the necessary attributes for an application to perform OAuth with Cognito
 */
export class CognitoOAuthSecret extends secretsmanager.Secret {
  constructor(scope: Construct, id: string, props: ICognitoOAuthSecretProps) {
    if (!props.client.userPoolClientSecret) {
      throw new Error(
        "Cognito client must be created with 'generateSecret' set to true",
      );
    }

    super(scope, id, {
      secretObjectValue: {
        // Only the userPoolClientSecret actually needs to be "secret", so the unsafePlainTexts
        // here shouldn't be an issue:
        clientId: cdk.SecretValue.unsafePlainText(
          props.client.userPoolClientId,
        ),
        clientSecret: props.client.userPoolClientSecret,
        issuer: cdk.SecretValue.unsafePlainText(
          `https://cognito-idp.${cdk.Aws.REGION}.amazonaws.com/${props.userPool.userPoolId}`,
        ),
      },
    });
    NagSuppressions.addResourceSuppressions(this, [
      {
        id: "AwsSolutions-SMG4",
        reason: "Secret rotation is not required for this demo",
      },
    ]);
  }
}

/**
 * Generate a globally-unique but repeatable domain prefix dependent on deployment context
 *
 * This method uses logic inspired by CDK's generatePhysicalName, which is a private method so we
 * can't use that API directly. We also tweak it a little to support passing a user-specified
 * prefix, and allocating remaining character budget depending how long that prefix is.
 *
 * Most of the function is generic, but the default maxLength is tuned for Cognito domains.
 *
 * @see https://github.com/aws/aws-cdk/blob/main/packages/aws-cdk-lib/core/lib/private/physical-name-generator.ts
 */
export function generateUniqueDomainName(
  scope: Construct,
  config: {
    maxLength?: number;
    prefix?: string;
  },
): string {
  const prefix = config.prefix || "";
  // Max length of a Cognito domain prefix is 63 per:
  // https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_CreateUserPoolDomain.html#CognitoUserPools-CreateUserPoolDomain-request-Domain
  // However, in practice we see validation errors whenever the *overall domain* exceeds
  // this limit - meaning we only have about 24-27 (depending on the region name)
  const maxLength = config.maxLength || 24;

  let nFreeChars = maxLength - prefix.length;
  if (nFreeChars < 0) {
    throw new Error(
      `Prefix '${prefix}' is longer than the maximum length ${maxLength}`,
    );
  }

  const stack = cdk.Stack.of(scope);
  const nodeUniqueId = cdk.Names.nodeUniqueId(scope.node);

  let region: string = stack.region;
  if (cdk.Token.isUnresolved(region) || !region) {
    throw new Error(
      `Cannot generate a unique ID for ${scope.node.path}, because the region is un-resolved or missing`,
    );
  }

  const account: string = stack.account;
  if (cdk.Token.isUnresolved(account) || !account) {
    throw new Error(
      `Cannot generate a unique ID for ${scope.node.path}, because the account is un-resolved or missing`,
    );
  }

  const unknownStackName = cdk.Token.isUnresolved(stack.stackName);
  const sha256 = crypto
    .createHash("sha256")
    .update(prefix)
    .update(nodeUniqueId)
    .update(region)
    .update(account);

  if (!unknownStackName) sha256.update(stack.stackName);

  let maxHashLen: number;
  if (nFreeChars <= 8) {
    maxHashLen = nFreeChars;
  } else {
    maxHashLen = Math.floor(6 + (nFreeChars - 6) / 3);
  }
  const hashPart = sha256.digest("hex").slice(0, maxHashLen);
  nFreeChars -= hashPart.length;

  let maxIdPartLen: number;
  if (nFreeChars <= 4 || unknownStackName) {
    maxIdPartLen = nFreeChars;
  } else {
    maxIdPartLen = Math.floor(2 + (nFreeChars - 2) / 2);
  }
  // Need the condition because .slice(-0) returns whole string:
  const idPart = maxIdPartLen ? nodeUniqueId.slice(-maxIdPartLen) : "";
  nFreeChars -= idPart.length;

  const stackPart = unknownStackName
    ? ""
    : stack.stackName.slice(0, nFreeChars);
  const ret = [prefix, stackPart, idPart, hashPart].join("");
  return ret.toLowerCase();
}
