import boto3
import random
import time
import json

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
iam_client = boto3_session.client('iam')
account_number = boto3.client('sts').get_caller_identity().get('Account')
identity = boto3.client('sts').get_caller_identity()['Arn']

encryption_policy_name = f"bedrock-sample-rag-sp-{suffix}"
network_policy_name = f"bedrock-sample-rag-np-{suffix}"
access_policy_name = f'bedrock-sample-rag-ap-{suffix}'
bedrock_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{suffix}'
fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{suffix}'
s3_policy_name = f'AmazonBedrockS3PolicyForKnowledgeBase_{suffix}'
sm_policy_name = f'AmazonBedrockSecretPolicyForKnowledgeBase_{suffix}'
oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{suffix}'
bda_policy_name = f'AmazonBedrockBDAPolicyForKnowledgeBase_{suffix}'

sm_policy_flag = False

def create_bedrock_execution_role(bucket_name, region = None):
    if not region:
        region_name = boto3_session.region_name
    else:
        region_name = region
        
    foundation_model_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v1",
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v2:0"
                ]
            }
        ]
    }

    s3_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": f"{account_number}"
                    }
                }
            }
        ]
    }

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com" 
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    # create policies based on the policy documents
    fm_policy = iam_client.create_policy(
        PolicyName=fm_policy_name,
        PolicyDocument=json.dumps(foundation_model_policy_document),
        Description='Policy for accessing foundation model',
    )

    s3_policy = iam_client.create_policy(
        PolicyName=s3_policy_name,
        PolicyDocument=json.dumps(s3_policy_document),
        Description='Policy for reading documents from s3')

    # create bedrock execution role
    bedrock_kb_execution_role = iam_client.create_role(
        RoleName=bedrock_execution_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS and S3',
        MaxSessionDuration=3600
    )

    # fetch arn of the policies and role created above
    bedrock_kb_execution_role_arn = bedrock_kb_execution_role['Role']['Arn']
    s3_policy_arn = s3_policy["Policy"]["Arn"]
    fm_policy_arn = fm_policy["Policy"]["Arn"]
    

    # attach policies to Amazon Bedrock execution role
    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=fm_policy_arn
    )
    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=s3_policy_arn
    )
    return bedrock_kb_execution_role


def create_oss_policy_attach_bedrock_execution_role(collection_id, bedrock_kb_execution_role, region =  None):
    
    if not region:
        region_name = boto3_session.region_name
    else:
        region_name = region
    
    # define oss policy document
    oss_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "aoss:APIAccessAll"
                ],
                "Resource": [
                    f"arn:aws:aoss:{region_name}:{account_number}:collection/{collection_id}"
                ]
            }
        ]
    }
    oss_policy = iam_client.create_policy(
        PolicyName=oss_policy_name,
        PolicyDocument=json.dumps(oss_policy_document),
        Description='Policy for accessing opensearch serverless',
    )
    oss_policy_arn = oss_policy["Policy"]["Arn"]
    print("Opensearch serverless arn: ", oss_policy_arn)

    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=oss_policy_arn
    )
    return None


def create_policies_in_oss(vector_store_name, aoss_client, bedrock_kb_execution_role_arn):
    encryption_policy = aoss_client.create_security_policy(
        name=encryption_policy_name,
        policy=json.dumps(
            {
                'Rules': [{'Resource': ['collection/' + vector_store_name],
                           'ResourceType': 'collection'}],
                'AWSOwnedKey': True
            }),
        type='encryption'
    )

    network_policy = aoss_client.create_security_policy(
        name=network_policy_name,
        policy=json.dumps(
            [
                {'Rules': [{'Resource': ['collection/' + vector_store_name],
                            'ResourceType': 'collection'}],
                 'AllowFromPublic': True}
            ]),
        type='network'
    )
    access_policy = aoss_client.create_access_policy(
        name=access_policy_name,
        policy=json.dumps(
            [
                {
                    'Rules': [
                        {
                            'Resource': ['collection/' + vector_store_name],
                            'Permission': [
                                'aoss:CreateCollectionItems',
                                'aoss:DeleteCollectionItems',
                                'aoss:UpdateCollectionItems',
                                'aoss:DescribeCollectionItems'],
                            'ResourceType': 'collection'
                        },
                        {
                            'Resource': ['index/' + vector_store_name + '/*'],
                            'Permission': [
                                'aoss:CreateIndex',
                                'aoss:DeleteIndex',
                                'aoss:UpdateIndex',
                                'aoss:DescribeIndex',
                                'aoss:ReadDocument',
                                'aoss:WriteDocument'],
                            'ResourceType': 'index'
                        }],
                    'Principal': [identity, bedrock_kb_execution_role_arn],
                    'Description': 'Easy data policy'}
            ]),
        type='data'
    )
    return encryption_policy, network_policy, access_policy


def delete_iam_role_and_policies():
    fm_policy_arn = f"arn:aws:iam::{account_number}:policy/{fm_policy_name}"
    s3_policy_arn = f"arn:aws:iam::{account_number}:policy/{s3_policy_name}"
    oss_policy_arn = f"arn:aws:iam::{account_number}:policy/{oss_policy_name}"
    sm_policy_arn = f"arn:aws:iam::{account_number}:policy/{sm_policy_name}"
    bda_policy_arn = f'arn:aws:iam::{account_number}:policy/{bda_policy_name}'



    iam_client.detach_role_policy(
        RoleName=bedrock_execution_role_name,
        PolicyArn=s3_policy_arn
    )
    iam_client.detach_role_policy(
        RoleName=bedrock_execution_role_name,
        PolicyArn=fm_policy_arn
    )
    iam_client.detach_role_policy(
        RoleName=bedrock_execution_role_name,
        PolicyArn=oss_policy_arn
    )
    iam_client.detach_role_policy(
        RoleName=bedrock_execution_role_name,
        PolicyArn=bda_policy_arn
    )
    # Delete Secrets manager policy only if it was created (i.e. for Confluence, SharePoint or Salesforce data source)
    if sm_policy_flag:
        iam_client.detach_role_policy(
            RoleName=bedrock_execution_role_name,
            PolicyArn=sm_policy_arn
        )
        iam_client.delete_policy(PolicyArn=sm_policy_arn)

    iam_client.delete_role(RoleName=bedrock_execution_role_name)
    iam_client.delete_policy(PolicyArn=s3_policy_arn)
    iam_client.delete_policy(PolicyArn=fm_policy_arn)
    iam_client.delete_policy(PolicyArn=oss_policy_arn)
    iam_client.delete_policy(PolicyArn=bda_policy_arn)
    
    return 0


def interactive_sleep(seconds: int):
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)

def create_bedrock_execution_role_multi_ds(bucket_names = None, secrets_arns = None, region = None):
    if not region:
        region_name = boto3_session.region_name
    else:
        region_name = region
    
    # 0. Create bedrock execution role

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com" 
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # create bedrock execution role
    bedrock_kb_execution_role = iam_client.create_role(
        RoleName=bedrock_execution_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS, secrets manager and S3',
        MaxSessionDuration=3600
    )

    # fetch arn of the role created above
    bedrock_kb_execution_role_arn = bedrock_kb_execution_role['Role']['Arn']

    # 1. Create and attach policy for foundation models
    foundation_model_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v1",
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v2:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/cohere.rerank-v3-5:0",
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.nova-micro-v1:0"
                ]
            }
        ]
    }
    
    fm_policy = iam_client.create_policy(
        PolicyName=fm_policy_name,
        PolicyDocument=json.dumps(foundation_model_policy_document),
        Description='Policy for accessing foundation model',
    )
  
    # fetch arn of this policy 
    fm_policy_arn = fm_policy["Policy"]["Arn"]
    
    # attach this policy to Amazon Bedrock execution role
    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=fm_policy_arn
    )

    # 2. Create and attach policy for s3 bucket
    if bucket_names:
        s3_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [item for sublist in [[f'arn:aws:s3:::{bucket}', f'arn:aws:s3:::{bucket}/*'] for bucket in bucket_names] for item in sublist], 
                    "Condition": {
                        "StringEquals": {
                            "aws:ResourceAccount": f"{account_number}"
                        }
                    }
                }
            ]
        }
        # Create policies based on the policy documents
        s3_policy = iam_client.create_policy(
            PolicyName=s3_policy_name,
            PolicyDocument=json.dumps(s3_policy_document),
            Description='Policy for reading documents from s3')

        # fetch arn of this policy 
        s3_policy_arn = s3_policy["Policy"]["Arn"]
        
        # attach this policy to Amazon Bedrock execution role
        iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=s3_policy_arn
        )

    # 3. Create and attach policy for secrets manager
    if secrets_arns:
        sm_policy_flag=True
        secrets_manager_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:PutSecretValue"
                    ],
                    "Resource": secrets_arns
                }
            ]
        }
        # Create policies based on the policy documents
        
        secrets_manager_policy = iam_client.create_policy(
            PolicyName=sm_policy_name,
            PolicyDocument=json.dumps(secrets_manager_policy_document),
            Description='Policy for accessing secret manager',
        )

        # fetch arn of this policy
        sm_policy_arn = secrets_manager_policy["Policy"]["Arn"]

        # attach policy to Amazon Bedrock execution role
        iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=sm_policy_arn
        )

    # 4. Create and attach policy for BDA
    bda_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BDAGetStatement",
                "Effect": "Allow",
                "Action": [
                    "bedrock:GetDataAutomationStatus"
                ],
                "Resource": f"arn:aws:bedrock:{region_name}:{account_number}:data-automation-invocation/*"
            },
            {
                "Sid": "BDAInvokeStatement",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeDataAutomationAsync"
                ],
                "Resource": f"arn:aws:bedrock:{region_name}:aws:data-automation-project/public-rag-default"
            }
        ]
    }
    
    bda_policy = iam_client.create_policy(
        PolicyName=bda_policy_name,
        PolicyDocument=json.dumps(bda_policy_document),
        Description='Policy for accessing BDA',
    )
  
    # fetch arn of this policy 
    bda_policy_arn = bda_policy["Policy"]["Arn"]
    
    # attach this policy to Amazon Bedrock execution role
    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=bda_policy_arn
    )
    return bedrock_kb_execution_role


def create_bedrock_execution_role_structured_rag(workgroup_arn, secrets_arn = None):

    # 0. Create bedrock execution role

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com" 
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # create bedrock execution role
    bedrock_kb_execution_role = iam_client.create_role(
        RoleName=bedrock_execution_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Amazon Bedrock Knowledge Base Execution Role for accessing redshift, and secrets manager',
        MaxSessionDuration=3600
    )

    # fetch arn of the role created above
    bedrock_kb_execution_role_arn = bedrock_kb_execution_role['Role']['Arn']

    # 1. Cretae and attach policy for foundation models
    redshift_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "RedshiftDataAPIStatementPermissions",
                "Effect": "Allow",
                "Action": [
                    "redshift-data:GetStatementResult",
                    "redshift-data:DescribeStatement",
                    "redshift-data:CancelStatement"
                ],
                "Resource": [
                    "*"
                ],
                "Condition": {
                "StringEquals": {
                    "redshift-data:statement-owner-iam-userid": "${aws:userid}"
                    }
                }
            },
            {
            "Sid": "RedshiftDataAPIExecutePermissions",
            "Effect": "Allow",
            "Action": [
                "redshift-data:ExecuteStatement"
            ],
            "Resource": [
                f"{workgroup_arn}"
            ]
        },
        # {
        #     "Sid": "RedshiftServerlessGetCredentials",
        #     "Effect": "Allow",
        #     "Action": "redshift-serverless:GetCredentials",
        #     "Resource": [
        #         f"{workgroup_arn}"
        #     ]
        # },
    
        {
            "Sid": "GetSecretPermissions",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                f"{secrets_arns}"
            ]
        },
        {
            "Sid": "SqlWorkbenchAccess",
            "Effect": "Allow",
            "Action": [
                "sqlworkbench:GetSqlRecommendations",
                "sqlworkbench:PutSqlGenerationContext",
                "sqlworkbench:GetSqlGenerationContext",
                "sqlworkbench:DeleteSqlGenerationContext"
            ],
            "Resource": "*"
        },
        {
            "Sid": "KbAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:GenerateQuery"
            ],
            "Resource": "*"
        }
        ]
    }
    
    redshift_policy = iam_client.create_policy(
        PolicyName=fm_policy_name,
        PolicyDocument=json.dumps(redshift_policy_document),
        Description='Policy for redshift workgroup',
    )
  
    # fetch arn of this policy 
    redshift_policy_arn = redshift_policy["Policy"]["Arn"]
    
    # attach this policy to Amazon Bedrock execution role
    iam_client.attach_role_policy(
        RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
        PolicyArn=redshift_policy_arn
    )

    return bedrock_kb_execution_role