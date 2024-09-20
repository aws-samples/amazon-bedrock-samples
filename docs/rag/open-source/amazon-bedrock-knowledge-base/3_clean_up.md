<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>


<h2>Clean up</h2>

Please make sure to comment the below section if you are planning to use the Knowledge Base that you created above for building your RAG application.

If you have been through all the examples in this current directory and no longer need the Knowledge Base, then please make sure to delete all the resources that were created as you will be incurred cost for storing documents in OSS index.

<h2>Steps for Deleting KnowledgeBase</h2>



```python
%store -r
```


```python
import boto3
```


```python
boto3_session = boto3.Session()
bedrock_agent_client = boto3_session.client('bedrock-agent', region_name=boto3_session.region_name)
aoss_client = boto3.client('opensearchserverless')
s3_client = boto3_session.client('s3', region_name=boto3_session.region_name)
iam_client = boto3.client("iam")
```

<h2>Delete Bedrock KnowledgeBase Data Sources</h2>


```python
response = bedrock_agent_client.list_data_sources(
    knowledgeBaseId=kb_id,
)
data_source_ids = [ x['dataSourceId'] for x in response['dataSourceSummaries']]

for data_source_id in data_source_ids:
    bedrock_agent_client.delete_data_source(dataSourceId = data_source_id, knowledgeBaseId=kb_id)
```

<h2>Remove KnowledgeBases and OpenSearch Collection</h2>


```python
response = bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
```


```python
kb_role_name = response['knowledgeBase']['roleArn'].split("/")[-1]
```


```python
kb_attached_role_policies_response = iam_client.list_attached_role_policies(
    RoleName=kb_role_name)
```


```python
kb_attached_role_policies = kb_attached_role_policies_response['AttachedPolicies']
```


```python
bedrock_agent_client.delete_knowledge_base(knowledgeBaseId=kb_id)
aoss_client.delete_collection(id=collection['createCollectionDetail']['id'])
aoss_client.delete_access_policy(type="data", name=access_policy['accessPolicyDetail']['name'])
aoss_client.delete_security_policy(type="network", name=network_policy['securityPolicyDetail']['name'])
aoss_client.delete_security_policy(type="encryption", name=encryption_policy['securityPolicyDetail']['name'])
```

<h2>Delete role and policies</h2>


```python
for policy in kb_attached_role_policies:
    iam_client.detach_role_policy(
            RoleName=kb_role_name,
            PolicyArn=policy['PolicyArn']
    )
```


```python
iam_client.delete_role(RoleName=kb_role_name)
```


```python
for policy in kb_attached_role_policies:
    iam_client.delete_policy(PolicyArn=policy['PolicyArn'])
```

<h2>Delete S3 objects</h2>


```python
objects = s3_client.list_objects(Bucket=bucket_name)
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
s3_client.delete_bucket(Bucket=bucket_name)
```
