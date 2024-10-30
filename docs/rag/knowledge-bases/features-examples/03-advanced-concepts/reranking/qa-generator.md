---
tags:
    - Prompt-Engineering
    - RAG/ Data-Ingestion
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/03-advanced-concepts/reranking/qa-generator.ipynb){:target="_blank"}"

<h2>Use LLM to Generate Question And Answer For Q&A conversational chatbot</h2>


```python
%load_ext autoreload
%autoreload 2
```


```python
import boto3
import urllib.request
import math
from utils import helper
```


```python
bedrock_runtime = boto3.client("bedrock-runtime")
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
```


```python
target_url = "https://www.gutenberg.org/ebooks/64317.txt.utf-8" # the great gatsby
data = urllib.request.urlopen(target_url)
my_texts = []
for line in data:
    my_texts.append(line.decode())
```


```python
doc_size = 700 # size of the document to determine number of batches
batches = math.ceil(len(my_texts) / doc_size)
```


```python
start = 0
data_samples = {}
data_samples['question'] = []
data_samples['ground_truth'] = []
for batch in range(batches):
    batch_text_arr = my_texts[start:start+doc_size]
    batch_text = "".join(batch_text_arr)
    start += doc_size
    ds = helper.generate_questions(bedrock_runtime, model_id, batch_text)
    data_samples['question'].extend(ds['question'])
    data_samples['ground_truth'].extend(ds['ground_truth'])
```


```python
data_samples
```


```python
import json
```


```python
with open("data/qa_samples.json", "w") as f:
    f.write(json.dumps(data_samples))
```


```python
batches
```


```python

```
