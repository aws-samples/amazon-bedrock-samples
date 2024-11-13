---
tags:
    - RAG/ Knowledge-Bases
    - Open Source/ Langchain
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/03-advanced-concepts/reranking/01_deploy-reranking-model-sm.ipynb){:target="_blank"}"

<h2>Reranking Model with Hugging Face Transformers and Amazon SageMaker</h2>
The goal of using a reranking model is to improve search relevance by reordering the result set returned by a retriever using a different model.

We will use the Hugging Face Inference DLCs and Amazon SageMaker Python SDK to create a real-time inference endpoint running a [BGE-Large](https://huggingface.co/BAAI/bge-reranker-large) as a reranking model. 

Currently, the SageMaker Hugging Face Inference Toolkit supports the pipeline feature from Transformers for zero-code deployment. This means you can run compatible Hugging Face Transformer models without providing pre- & post-processing code. 

Using SageMaker SDK to deploy a model from HuggingFace, you can override the following methods:

* model_fn(model_dir) overrides the default method for loading a model. The return value model will be used in thepredict_fn for predictions.
* model_dir is the the path to your unzipped model.tar.gz.
* input_fn(input_data, content_type) overrides the default method for pre-processing. The return value data will be used in predict_fn for predictions. The inputs are:
* input_data is the raw body of your request.
* content_type is the content type from the request header.
* predict_fn(processed_data, model) overrides the default method for predictions. The return value predictions will be used in output_fn.
* model returned value from model_fn methond

First, let's make sure we are using the latest sagemaker library


```python
%pip install sagemaker -Uq
```


```python
<h2>restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

Install git-lfs for downloading the huggingface model from HF model hub.


```python
!sudo apt-get update -y 
!curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
!sudo apt-get install git-lfs git -y
```

<h2>Initialize SageMaker Session</h2>
Initialize a sagemaker session and define an IAM role for deploying the reranking model


```python
import sagemaker
import boto3
from sagemaker.huggingface import HuggingFaceModel

sess = sagemaker.Session()
try:
	role = sagemaker.get_execution_role()
except ValueError:
	iam = boto3.client('iam')
	role = iam.get_role(RoleName='sagemaker_execution_role')['Role']['Arn']
```

<h2>Create custom an inference.py script</h2>
To use the custom inference script, you need to create an inference.py script. 
In our example, we are going to overwrite the model_fn to load our reranking model correctly and the predict_fn to predict the scores for each input pair.


```python
!mkdir -p code
```


```python
%%writefile code/inference.py

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

def model_fn(model_dir):
  # Load model from HuggingFace Hub
  tokenizer = AutoTokenizer.from_pretrained(model_dir)
  model = AutoModelForSequenceClassification.from_pretrained(model_dir)
  model.eval()
  return model, tokenizer

def predict_fn(data, model_and_tokenizer):
    model, tokenizer = model_and_tokenizer
    query = data['query']
    documents = data['documents']
    topk = data['topk']
    pair_list = [ [ query, x ] for x in documents ]
    with torch.no_grad():
        inputs = tokenizer(pair_list, padding=True, truncation=True, return_tensors='pt', max_length=512)
        scores = model(**inputs, return_dict=True).logits.view(-1, ).float()
        print(scores)
        sorted_indexes = sorted(range(len(scores)), key=lambda k: scores[k], reverse=True)[:topk]
        response = [ { "index" : x, "score" : scores[x] } for x in sorted_indexes ]
        return response
```

<h2>Create model.tar.gz with inference script and model</h2>
To use our inference.py we need to bundle it into a `model.tar.gz` archive with all our model-artifcats, e.g. `pytorch_model.bin`. The `inference.py` script will be placed into a code/ folder. We will use `git` and `git-lfs` to easily download our model from hf.co/models and upload it to Amazon S3 so we can use it when creating our SageMaker endpoint.


```python
repository = "BAAI/bge-reranker-large" # Define the reranking HF model ID
model_id=repository.split("/")[-1]
```

1. Download the model from hf.co/models with git clone.


```python
!git lfs install
!git clone https://huggingface.co/$repository
```

2. copy inference.py into the code/ directory of the model directory.


```python
!rm -rf code/.ipynb_checkpoints/
!cp -r ./code/ $model_id/code/
```

3. Create a `model.tar.gz` archive with all the model artifacts and the `inference.py` script.


```python
%cd $model_id
!tar zcvf model.tar.gz *
```

4. Upload the model.tar.gz to Amazon S3:


```python
s3_location=f"s3://{sess.default_bucket()}/custom_inference/{model_id}/model.tar.gz"
```


```python
!aws s3 cp model.tar.gz $s3_location
```

<h2>Create custom HuggingfaceModel</h2>
After we have created and uploaded our `model.tar.gz` archive to Amazon S3. Can we create a custom `HuggingfaceModel` class. This class will be used to create and deploy our SageMaker endpoint.


```python
<h2>create Hugging Face Model Class</h2>
huggingface_model = HuggingFaceModel(
    model_data=s3_location,       # path to your model and script
	transformers_version='4.37.0',
	pytorch_version='2.1.0',
	py_version='py310',
	role=role,
    env = { "SAGEMAKER_PROGRAM" : "inference.py" },
    sagemaker_session=sess
)

<h2>deploy model to SageMaker Inference</h2>
predictor = huggingface_model.deploy(
	initial_instance_count=1, # number of instances
	instance_type='ml.m5.xlarge' # ec2 instance type
)
```

<h2>Test </h2>
In the following, we are going to test the deployed endpoint to ensure it will return the ranked documents using the reranker model


```python
query = "what is panda?"
documents = ['hi', "panda is a restaurant", 'The giant panda (Ailuropoda melanoleuca), sometimes called a panda bear or simply panda, is a bear species endemic to China.']
topk = 2
response = predictor.predict({
	"query": query,
    "documents" : documents,
    "topk" : topk
})
```


```python
predictor.deserializer
```


```python
response
```


```python
reranking_model_endpoint = predictor.endpoint_name
```


```python
%store reranking_model_endpoint
```

<h2>Next Step</h2>
Congratulations. You have completed the reranking model deployment step. You can now build a RAG application that integrates with a reranking model. 
Let's open the [kb-reranker.ipynb](kb-reranker.ipynb) file and follow the instructions. 
