#Source: https://github.com/aws-samples/titan-multimodal-embeddings-workshop/blob/main/3-content-search/aoss_utils.py

# Opensearch Collection Creation Functions
import botocore
import time


def createEncryptionPolicy(client, collection_name):
    """Creates an encryption policy that matches all collections beginning with your collection name"""
    try:
        response = client.create_security_policy(
            description="Encryption policy for {} collections".format(collection_name),
            name="{}-policy".format(collection_name),
            policy="""
                {
                    \"Rules\":[
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[
                                \"collection\/{}*\"
                            ]
                        }
                    ],
                    \"AWSOwnedKey\":true
                }
                """.replace("{}", collection_name),
            type='encryption'
        )
        print('\nEncryption policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] The policy name or rules conflict with an existing policy.')
        else:
            raise error


def createNetworkPolicy(client, collection_name):
    """Creates a network policy that matches all collections beginning with your collection name"""
    try:
        response = client.create_security_policy(
            description="Network policy for {} collections".format(collection_name),
            name="{}-policy".format(collection_name),
            policy="""
                [{
                    \"Description\":\"Public access for {} collection\",
                    \"Rules\":[
                        {
                            \"ResourceType\":\"dashboard\",
                            \"Resource\":[\"collection\/{}*\"]
                        },
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[\"collection\/{}*\"]
                        }
                    ],
                    \"AllowFromPublic\":true
                }]
                """.replace("{}", collection_name),
            type='network'
        )
        print('\nNetwork policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A network policy with this name already exists.')
        else:
            raise error


def createAccessPolicy(client, collection_name, identity_arn):
    """Creates a data access policy that matches all collections beginning with your collection name"""
    try:
        policy =  """
                [{
                    \"Rules\":[
                        {
                            \"Resource\":[
                                \"index\/{}*\/*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateIndex\",
                                \"aoss:DeleteIndex\",
                                \"aoss:UpdateIndex\",
                                \"aoss:DescribeIndex\",
                                \"aoss:ReadDocument\",
                                \"aoss:WriteDocument\"
                            ],
                            \"ResourceType\": \"index\"
                        },
                        {
                            \"Resource\":[
                                \"collection\/{}*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateCollectionItems\"
                            ],
                            \"ResourceType\": \"collection\"
                        }
                    ],
                    \"Principal\":[
                        \"{identity_arn}"
                    ]
                }]
                """.replace("{}", collection_name)
        policy = policy.replace("{identity_arn}", identity_arn)
        response = client.create_access_policy(
            description='Data access policy for mvc collections',
            name="{}-policy".format(collection_name),
            policy=policy,
            type='data'
        )
        print('\nAccess policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] An access policy with this name already exists.')
        else:
            raise error


def createCollection(client, collection_name):
    """Creates a collection"""
    try:
        response = client.create_collection(
            name=collection_name,
            type='VECTORSEARCH'
        )
        return(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A collection with this name already exists. Try another name.')
        else:
            raise error


def waitForCollectionCreation(client, collection_name):
    """Waits for the collection to become active"""
    response = client.batch_get_collection(
        names=[collection_name])
    # Periodically check collection status
    while (response['collectionDetails'][0]['status']) == 'CREATING':
        print('Creating collection...')
        time.sleep(30)
        response = client.batch_get_collection(
            names=[collection_name])
    print('\nCollection successfully created:')
    print(response["collectionDetails"])
    host = (response['collectionDetails'][0]['collectionEndpoint'])
    return host.replace("https://", "") , response['collectionDetails'][0]['id']