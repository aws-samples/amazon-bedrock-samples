---
tags:
    - RAG/ Data-Ingestion
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/use-case-examples/rag-using-structured-unstructured-data/0-create-dummy-structured-data.ipynb){:target="_blank"}"

<h2>Context:</h2>
The purpose of this notebook is to generate synthetic tabular data that you can use for the `Rag with structured and unstructed data` workshop.

This notebook, run predefined python scripts in `pythonScripts` folder to generate dummy data. The generated data is saved in four csv files inside `sds` folder. SDS here means sythetic dataset.


```python
!pip install faker
```


```python
<h2>Execute the files in Directory:</h2>
import os

files = os.listdir('pythonScripts')

directory = 'sds'
if not os.path.exists(directory):
    print(f'directory not found, creating {directory} directory')
    os.makedirs(directory)
            
for file_name in files:
    if file_name.endswith('.py'):
        print(f"Running {file_name}")
        %run pythonScripts/{file_name}
```

<h2>End</h2>
