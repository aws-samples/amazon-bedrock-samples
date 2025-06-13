import * as cdk from "aws-cdk-lib";
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from "constructs";
import { NagSuppressions } from "cdk-nag";


/**
 * Interface for configuring Cognito authentication
 * @interface ICognitoProps
 * @property {string} loadBalancerUrl - The URL of the load balancer for callback/logout URLs
 * @property {string} [userPoolId] - Optional existing Cognito User Pool ID to use instead of creating new one
 * @property {boolean} [createDomain] - Whether to create a Cognito domain, defaults to false
 * @property {string} [userPoolDomainPrefix] - Prefix for the Cognito domain if createDomain is true
 */
export interface ICognitoProps {
    loadBalancerUrl: string;
    userPoolId?: string;
    createDomain?: boolean;
    userPoolDomainPrefix?: string;
    createSecret?: boolean;
    /**
     * @default true
     */
}


export class CognitoAuth extends Construct {
    public readonly cognitoSecret: cdk.aws_secretsmanager.Secret;

    constructor(scope: Construct, id: string, props: ICognitoProps) {
        super(scope, id);

        const userPool = props.userPoolId
            ? cognito.UserPool.fromUserPoolId(this, 'UserPool', props.userPoolId)
            : new cognito.UserPool(this, 'UserPool', {
                selfSignUpEnabled: false,
                signInAliases: {
                    email: true, username: true
                },
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
                removalPolicy: cdk.RemovalPolicy.DESTROY,
                accountRecovery: cognito.AccountRecovery.EMAIL_ONLY
            });

        const domain = props.createDomain
            ? new cognito.UserPoolDomain(this, 'UserPoolDomain', {
                userPool,
                cognitoDomain: { domainPrefix: props.userPoolDomainPrefix || 'langfuse-demo' }
            }) : {};

        NagSuppressions.addResourceSuppressions(userPool, [
            { id: 'AwsSolutions-COG2', reason: 'MFA is not required for this demo' },
        ]);
        NagSuppressions.addResourceSuppressions(userPool, [
            { id: 'AwsSolutions-COG3', reason: 'AdvancedSecurityMode is not required for this demo' },
        ]);


        const userPoolClient = userPool.addClient('UserPoolClient', {
            userPoolClientName: 'LangfuseWebApp',
            generateSecret: true,
            oAuth: {
                callbackUrls: [props.loadBalancerUrl.concat('/api/auth/callback/cognito')],
                logoutUrls: [props.loadBalancerUrl.concat('/auth/sign-in')],
                scopes: [
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
        })

        this.cognitoSecret = new cdk.aws_secretsmanager.Secret(this, 'CognitoSecret', {
            secretObjectValue: {
                AUTH_COGNITO_CLIENT_ID: cdk.SecretValue.unsafePlainText(userPoolClient.userPoolClientId),
                AUTH_COGNITO_CLIENT_SECRET: userPoolClient.userPoolClientSecret,
                AUTH_COGNITO_ISSUER: cdk.SecretValue.unsafePlainText(`https://cognito-idp.${cdk.Aws.REGION}.amazonaws.com/${userPool.userPoolId}`)
            },
            secretName: 'CognitoSecret',
        });
        NagSuppressions.addResourceSuppressions(this.cognitoSecret, [
            { id: 'AwsSolutions-SMG4', reason: 'Secret rotation is not required for this demo' },
        ]);
    }

}