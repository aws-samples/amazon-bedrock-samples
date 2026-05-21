from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, RequestError
from IPython.display import clear_output, HTML, display
import time
import json
import uuid
import boto3
import os
import pprint
import random 
from urllib.parse import urlparse


pp = pprint.PrettyPrinter(indent=2)


def play_video(video_url: str, start_time: float) -> None:
    """
    Play a video at a specific start time.

    Args:
        video_url (str): The URL of the video to play.
        start_time (float): The start time of the video in seconds.
    """

    # HTML code for the video player
    html_code = f"""
    <video width="640" controls>
        <source src="{video_url}#t={start_time}" type="video/mp4">
    </video>
    """
    display(HTML(html_code))
    

def delete_s3_bucket_objects(s3_client, s3_bucket_name, s3_prefix):
    response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=s3_prefix)
    try:
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=s3_bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            print(f"✅ Bucket '{s3_bucket_name}' with prefix: {s3_prefix} emptied successfully.")
        else:
            print(f"✅ Bucket '{s3_bucket_name}' with prefix: {s3_prefix} is already empty.")
    except Exception as e:
        print(f"❌ Error emptying bucket '{s3_bucket_name}' with prefix: {s3_prefix}: {e}")

def interactive_sleep(seconds: int):
    """
    Support functionality to induce an artificial 'sleep' to the code in order to wait for resources to be available
    Args:
        seconds (int): number of seconds to sleep for
    """
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)

class OpenSearchServerlessHelper:
    """
    Support class that allows for:
        - creation (or retrieval) of a OpenSearch Server Collection
          (including OSS, IAM roles and Permissions and S3 bucket)
    """

    def __init__(self, suffix=None, host=None):
        """
        Class initializer
        """
        boto3_session = boto3.session.Session()
        self.region_name = boto3_session.region_name
        self.iam_client = boto3_session.client('iam',region_name=self.region_name)
        self.account_number = boto3_session.client('sts',region_name=self.region_name).get_caller_identity().get('Account')
        self.suffix = suffix if suffix else random.randrange(200, 900)
        self.identity = boto3_session.client('sts',region_name=self.region_name).get_caller_identity()['Arn']
        self.aoss_client = boto3_session.client('opensearchserverless',region_name=self.region_name)
        self.s3_client = boto3_session.client('s3',region_name=self.region_name)
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')
        if host:
            self.oss_client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )
        else:   
            self.oss_client = None

    def create_oss(self, collection_name_prefix):
        """
        Function used to create an OpenSearch Serverless Collection.

        """
        collection_name = f"{collection_name_prefix}-{self.suffix}"
        encryption_policy_name = f"{collection_name_prefix}-sp-{self.suffix}"
        network_policy_name = f"{collection_name_prefix}-np-{self.suffix}"
        access_policy_name = f'{collection_name_prefix}-ap-{self.suffix}'
        encryption_policy, network_policy, access_policy = self.create_policies_in_oss(
            encryption_policy_name, collection_name, network_policy_name, access_policy_name
        )
        host, collection, collection_id, collection_arn = self._create_oss(collection_name)
        # Build the OpenSearch client
        self.oss_client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )

        return host, collection, collection_id


    def create_policies_in_oss(
            self, encryption_policy_name: str, vector_store_name: str, network_policy_name: str,
            access_policy_name: str
    ):
        """
        Create OpenSearch Serverless encryption, network and data access policies.
        If policies already exist, retrieve them
        Args:
            encryption_policy_name: name of the data encryption policy
            vector_store_name: name of the vector store
            network_policy_name: name of the network policy
            access_policy_name: name of the data access policy

        Returns:
            encryption_policy, network_policy, access_policy
        """
        try:
            encryption_policy = self.aoss_client.create_security_policy(
                name=encryption_policy_name,
                policy=json.dumps(
                    {
                        'Rules': [{'Resource': ['collection/' + vector_store_name],
                                   'ResourceType': 'collection'}],
                        'AWSOwnedKey': True
                    }),
                type='encryption'
            )
        except self.aoss_client.exceptions.ConflictException:
            print(f"{encryption_policy_name} already exists, retrieving it!")
            encryption_policy = self.aoss_client.get_security_policy(
                name=encryption_policy_name,
                type='encryption'
            )

        try:
            network_policy = self.aoss_client.create_security_policy(
                name=network_policy_name,
                policy=json.dumps(
                    [
                        {'Rules': [{'Resource': ['collection/' + vector_store_name],
                                    'ResourceType': 'collection'}],
                         'AllowFromPublic': True}
                    ]),
                type='network'
            )
        except self.aoss_client.exceptions.ConflictException:
            print(f"{network_policy_name} already exists, retrieving it!")
            network_policy = self.aoss_client.get_security_policy(
                name=network_policy_name,
                type='network'
            )

        try:
            access_policy = self.aoss_client.create_access_policy(
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
                            'Principal': [self.identity],
                            'Description': 'Easy data policy'}
                    ]),
                type='data'
            )
        except self.aoss_client.exceptions.ConflictException:
            print(f"{access_policy_name} already exists, retrieving it!")
            access_policy = self.aoss_client.get_access_policy(
                name=access_policy_name,
                type='data'
            )
        return encryption_policy, network_policy, access_policy

    def _create_oss(self, collection_name: str):
        """
        Create OpenSearch Serverless Collection. If already existent, retrieve
        Args:
            collection_name: name of the OSS collection
        """
        try:
            collection = self.aoss_client.create_collection(
                name=collection_name, type='VECTORSEARCH'
            )
            collection_id = collection['createCollectionDetail']['id']
            collection_arn = collection['createCollectionDetail']['arn']
        except self.aoss_client.exceptions.ConflictException:
            collection = self.aoss_client.batch_get_collection(
                names=[collection_name]
            )['collectionDetails'][0]
            pp.pprint(collection)
            collection_id = collection['id']
            collection_arn = collection['arn']
        pp.pprint(collection)

        # Get the OpenSearch serverless collection URL
        host = collection_id + '.' + self.region_name + '.aoss.amazonaws.com'
        print(host)
        # wait for collection creation
        # This can take couple of minutes to finish
        response = self.aoss_client.batch_get_collection(names=[collection_name])
        # Periodically check collection status
        while (response['collectionDetails'][0]['status']) == 'CREATING':
            print('Creating collection...')
            interactive_sleep(30)
            response = self.aoss_client.batch_get_collection(names=[collection_name])
        print('\nCollection successfully created:')
        pp.pprint(response["collectionDetails"])
        # create opensearch serverless access policy and attach it to Bedrock execution role
        return host, collection, collection_id, collection_arn


    def create_vector_index(self, index_name_prefix: str, schema_json):
        """
        Create OpenSearch Serverless vector index. If existent, ignore
        Args:
            index_name: name of the vector index
        """
        
        # Create index
        try:
            index_name = f"{index_name_prefix}-{self.suffix}"
            response = self.oss_client.indices.create(index=index_name, body=schema_json)
            print('\nCreating index:')
            pp.pprint(response)

            # index creation can take up to a minute
            interactive_sleep(60)
            return index_name
        except RequestError as e:
            # you can delete the index if its already exists
            # oss_client.indices.delete(index=index_name)
            print(
                f'Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to '
                f'delete, and recreate the index')
        except Exception as e:
            print(f"error: {e}")
    
    def index(self, index_name, doc):
        response = self.oss_client.index(
            index=index_name,
            body=json.dumps(doc),
            params={"timeout": 60},
        )
        return response

class BedrockTwelvelabsHelper():
    def __init__(self, bedrock_client, 
                s3_client, aws_account_id: str, model_id: str, cris_model_id: str, s3_bucket_name: str, region: str="us-east-1"):

        self.region = region
        self.aws_account_id = aws_account_id
        self.model_id = model_id
        self.cris_model_id = cris_model_id
        self.bedrock_client = bedrock_client
        self.s3_client= s3_client
        self.s3_bucket_name = s3_bucket_name
        self.s3_images_path = "images"
        self.s3_videos_path = "videos"
        self.s3_embeddings_path = "embeddings"
        self.video_embedding_mapping = {}
        self.opensearch_endpoint = None
        self.opensearch_client = None
        self.opensearch_serverless_collection_name = None
        self.index_name = None
        self.session = boto3.Session()
        self.oss_helper = None

    def upload_video(self, video_file_path) -> str:
        # Upload to S3
        s3_input_key = f'{self.s3_videos_path}/{os.path.basename(video_file_path)}'
        self.s3_client.upload_file(video_file_path, self.s3_bucket_name, s3_input_key)
        output_s3_path = f"s3://{self.s3_bucket_name}/{s3_input_key}"
        print(f"Uploaded to {output_s3_path}")
        return output_s3_path

    # Helper function to wait for async embedding results
    def wait_for_embedding_output(self, s3_prefix: str, 
                                invocation_arn: str, 
                                verbose: bool = False) -> list:
        """
        Wait for Bedrock async embedding task to complete and retrieve results

        Args:
            s3_bucket (str): The S3 bucket name
            s3_prefix (str): The S3 prefix for the embeddings
            invocation_arn (str): The ARN of the Bedrock async embedding task

        Returns:
            list: A list of embedding data
            
        Raises:
            Exception: If the embedding task fails or no output.json is found
        """
        
        # Wait until task completes
        status = None
        while status not in ["Completed", "Failed", "Expired"]:
            response = self.bedrock_client.get_async_invoke(invocationArn=invocation_arn)
            status = response['status']
            if verbose:
                clear_output(wait=True)
                print(f"Embedding task status: {status}")
            time.sleep(5)
        
        if status != "Completed":
            raise Exception(f"Embedding task failed with status: {status}")
        
        # Retrieve the output from S3
        response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket_name, Prefix=s3_prefix)
        
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('output.json'):
                output_key = obj['Key']
                obj = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=output_key)
                content = obj['Body'].read().decode('utf-8')
                data = json.loads(content).get("data", [])
                return data
        
        raise Exception("No output.json found in S3 prefix")


    # Create text embedding
    def create_text_embedding_async(self, text_query: str) -> list:
        """
        Create embeddings for text asynchronously using Marengo on Bedrock using asynchronous API

        Args:
            text_query (str): The text query to create an embedding for
            
        Returns:
            list: A list of embedding data
        """
        
        s3_output_prefix = f'{self.s3_embeddings_path}/text/{uuid.uuid4()}'
        
        response = self.bedrock_client.start_async_invoke(
            modelId=self.model_id,
            modelInput={
                "inputType": "text",
                "text": {
                    "inputText": text_query
                }
            },
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f's3://{self.s3_bucket_name}/{s3_output_prefix}'
                }
            }
        )
        
        invocation_arn = response["invocationArn"]
        print(f"Text embedding task started: {invocation_arn}")
        
        # Wait for completion and get results
        try:
            embedding_data = self.wait_for_embedding_output(s3_output_prefix, invocation_arn)
        except Exception as e:
            print(f"Error waiting for embedding output: {e}")
            return None
        
        return embedding_data

    def create_text_embedding(self, text_query: str) -> list:
        """
        Create embeddings for text synchronously using Marengo on Bedrock

        Args:
            text_query (str): The text query to create an embedding for
            
        Returns:
            list: A list of embedding data
        """
        
        modelInput={
                "inputType": "text",
                "text": {
                    "inputText": text_query
                }
        }
        response = self.bedrock_client.invoke_model(
            modelId=self.cris_model_id,
            body=json.dumps(modelInput)
        )
        
        result = json.loads(response["body"].read())
        return result["data"]

    # Create image embedding
    def create_image_embedding(self, image_path: str) -> list:
        """
        Create embeddings for image synchronously using Marengo on Bedrock
        
        Args:
            image_path (str): The path to the image to create an embedding for
            
        Returns:
            list: A list of embedding data
        """

        image_path_basename = os.path.basename(image_path)
        # Upload image to S3
        self.s3_client.upload_file(
            Filename=image_path,
            Bucket=self.s3_bucket_name,
            Key=f"{self.s3_images_path}/{image_path_basename}"
        )
        s3_image_uri = f's3://{self.s3_bucket_name}/{self.s3_images_path}/{image_path_basename}'
        modelInput={
                "inputType": "image",
                "image" : {
                    "mediaSource": {
                        "s3Location": {
                            "uri": s3_image_uri,
                            "bucketOwner": self.aws_account_id
                        }
                    }
                }
            }
        response = self.bedrock_client.invoke_model(
            modelId=self.cris_model_id,
            body=json.dumps(modelInput),
        )
        
        result = json.loads(response["body"].read())
        return result["data"]

    def create_image_embedding_async(self, image_path: str) -> list:
        """
        Create embeddings for image asynchronously using Marengo on Bedrock using asynchronous API
        
        Args:
            image_path (str): The path to the image to create an embedding for
            
        Returns:
            list: A list of embedding data
        """

        image_path_basename = os.path.basename(image_path)
        # Upload image to S3
        self.s3_client.upload_file(
            Filename=image_path,
            Bucket=self.s3_bucket_name,
            Key=f"{self.s3_images_path}/{image_path_basename}"
        )
        s3_image_uri = f's3://{self.s3_bucket_name}/{self.s3_images_path}/{image_path_basename}'
        s3_output_prefix = f'{self.s3_embeddings_path}/{self.s3_images_path}/{uuid.uuid4()}'
        
        response = self.bedrock_client.start_async_invoke(
            modelId=self.model_id,
            modelInput={
                "inputType": "image",
                "mediaSource": {
                    "s3Location": {
                        "uri": s3_image_uri,
                        "bucketOwner": self.aws_account_id
                    }
                }
            },
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f's3://{self.s3_bucket_name}/{s3_output_prefix}'
                }
            }
        )
        
        invocation_arn = response["invocationArn"]
        print(f"Image embedding task started: {invocation_arn}")
        
        # Wait for completion and get results
        try:
            embedding_data = self.wait_for_embedding_output(s3_output_prefix, invocation_arn)
        except Exception as e:
            print(f"Error waiting for embedding output: {e}")
            return None
        
        return embedding_data
        
    # Create video embedding
    def create_video_embedding(self, video_s3_uri: str) -> list:
        """
        Create embeddings for video using Marengo on Bedrock
        
        Args:
            video_s3_uri (str): The S3 URI of the video to create an embedding for
            
        Returns:
            list: A list of embedding data
        """
        
        unique_id = uuid.uuid4()
        s3_output_prefix = f'{self.s3_embeddings_path}/{self.s3_videos_path}/{unique_id}'
        
        response = self.bedrock_client.start_async_invoke(
            modelId=self.model_id,
            modelInput={
                "inputType": "video",
                "video" : {
                    "mediaSource": {
                        "s3Location": {
                            "uri": video_s3_uri,
                            "bucketOwner": self.aws_account_id
                        }
                    }
                }
            },
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f's3://{self.s3_bucket_name}/{s3_output_prefix}'
                }
            }
        )
        
        invocation_arn = response["invocationArn"]
        print(f"Video embedding task started: {invocation_arn}")
        
        # Wait for completion and get results
        try:
            embedding_data = self.wait_for_embedding_output(s3_output_prefix, invocation_arn)
            self.video_embedding_mapping[str(unique_id)] = video_s3_uri
        except Exception as e:
            print(f"Error waiting for embedding output: {e}")
            return None
        
        return embedding_data, str(unique_id)
    
    def create_opensearch_serverless_collection(self, collection_name_prefix: str):
        self.oss_helper = OpenSearchServerlessHelper()
        host, collection, _ = self.oss_helper.create_oss(collection_name_prefix)
        self.opensearch_endpoint = host
        self.opensearch_serverless_collection_name = collection
        self.opensearch_client = self.oss_helper.oss_client
        return host, collection
        
    def create_opensearch_index(self, index_name_prefix: str):
        if self.index_name:
            print(f"index already created previously. Not creating a new one")
            return self.index_name
        
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 1,
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 512,
                        "method": {
                            "engine": "faiss",
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                        },
                    },
                    "start_time": {"type": "float"},
                    "end_time": {"type": "float"},
                    "video_id": {"type": "keyword"},
                    "segment_text": {"type": "text"},
                    "embedding_option": {"type": "keyword"}
                }
            },
        }
        
        index_name = self.oss_helper.create_vector_index(index_name_prefix=index_name_prefix, schema_json=index_body)
        self.index_name = index_name
        return index_name
        

    # Index video embeddings in OpenSearch
    def index_video_embeddings(self, video_embeddings: list, video_id: str = "sample_video") -> int:
        """
        Index video embeddings into OpenSearch
        
        Args:
            os_client (OpenSearch): The OpenSearch client
            index_name (str): The name of the index to create
            video_embeddings (list): The list of video embeddings
            video_id (str): The id of the video

        Returns:
            int: The number of documents indexed
        """
        
        documents = []
        
        for i, segment in enumerate(video_embeddings):
            document = {
                "embedding": segment["embedding"],
                "start_time": segment["startSec"],
                "end_time": segment["endSec"],
                "video_id": video_id,
                "segment_id": i,
                "embedding_option": segment.get("embeddingOption", "visual")
            }
            documents.append(document)
        
        # Bulk index documents
        bulk_data = []
        for doc in documents:
            bulk_data.append({"index": {"_index": self.index_name}})
            bulk_data.append(doc)
        
        # Convert to bulk format
        bulk_body = "\n".join(json.dumps(item) for item in bulk_data) + "\n"
        
        response = self.opensearch_client.bulk(body=bulk_body, index=self.index_name)
        
        if response["errors"]:
            print("Some documents failed to index:")
            for item in response["items"]:
                if "index" in item and "error" in item["index"]:
                    print(f"Error: {item['index']['error']}")
        
        return len(documents)

    # Text Query Search Function
    def search_videos_by_text(self, query_text: str, top_k: int=5) -> list:
        """
        Search for video segments using text queries

        Args:
            query_text (str): The text query to search for.
            top_k (int): The number of videos to return.

        Returns:
            list: A list of video segments that match the query.
        """
        
        # Generate embedding for the text query
        print(f"Generating embedding for query: '{query_text}'")
        query_embedding_data = self.create_text_embedding(query_text)
        query_embedding = query_embedding_data[0]["embedding"]

        search_body = {
                        "query": {
                            "script_score": {
                            "query": {
                                "bool": {
                                    "filter": {
                                        "bool": {
                                            "must": [
                                                {
                                                    "term": {
                                                        "embedding_option": "visual"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            },
                            "script": {
                                    "source": "knn_score",
                                    "lang": "knn",
                                    "params": {
                                    "field": "embedding",
                                    "query_value": query_embedding,
                                    "space_type": "l2"
                                }
                            }
                        }
                    },
                        "_source": ["start_time", "end_time", "video_id", "segment_id", "embedding_option"],
                        "size": top_k,
                    }

        response = self.opensearch_client.search(index=self.index_name, body=search_body)

        print(f"\n✅ Found {len(response['hits']['hits'])} matching segments:")
        results = []

        for hit in response['hits']['hits']:
            print(hit)
            result = {
                "score": hit["_score"],
                "video_id": hit["_source"]["video_id"],
                "segment_id": hit["_source"]["segment_id"],
                "start_time": hit["_source"]["start_time"],
                "end_time": hit["_source"]["end_time"],
                "embedding_option": hit["_source"]["embedding_option"]
            }
            results.append(result)
            
            print(f" Score: {result['score']:.4f} | Video: {self.video_embedding_mapping[result['video_id']]} | "
                f"Segment: {result['segment_id']} | Embedding Option: {result["embedding_option"]} | Time: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
        return results


    # Image Query Search Function
    def search_videos_by_image(self, image_path: str, top_k: int=5) -> list:
        """
        Search for videos that contain the given image.

        Args:
            image_path (str): The path to the image to search for.
            top_k (int): The number of videos to return.

        Returns:
            list: A list of video segments that match the query.
        """
        print(f"Creating embeddings for image: {image_path}")
        embedding_data = self.create_image_embedding(image_path)
        query_embedding = embedding_data[0]["embedding"]

        # Search OpenSearch index
        search_body = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k
                    }
                }
            },
            "size": top_k,
            "_source": ["start_time", "end_time", "video_id", "segment_id"]
        }
        
        response = self.opensearch_client.search(index=self.index_name, body=search_body)
        
        print(f"\n✅ Found {len(response['hits']['hits'])} matching segments:")
        results = []
        
        for hit in response['hits']['hits']:
            result = {
                "score": hit["_score"],
                "video_id": hit["_source"]["video_id"],
                "segment_id": hit["_source"]["segment_id"],
                "start_time": hit["_source"]["start_time"],
                "end_time": hit["_source"]["end_time"]
            }
            results.append(result)
            
            print(f"  Score: {result['score']:.4f} | Video: {self.video_embedding_mapping[result['video_id']]} | "
                f"Segment: {result['segment_id']} | Time: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
        
        return results

    def find_video_from_embedding(self, embedding_data):
        video_s3_location = self.video_embedding_mapping[embedding_data["video_id"]]
        parsed = urlparse(video_s3_location)
        video_bucket = parsed.netloc
        video_key = parsed.path.lstrip('/')

        # Generate presigned URL for the video
        presigned_url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": video_bucket, "Key": video_key},
            ExpiresIn=3600
        )

        return presigned_url