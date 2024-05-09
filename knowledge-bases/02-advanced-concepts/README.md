# Advanced Concepts

## Contents
[0_chunk_size_evaluation_for_KB_RAG.ipynb](./01-chunking-strategy/0_chunk_size_evaluation_for_KB_RAG.ipynb) - This notebook provides sample code for chunking size evaluation for building optimum RAG applcation. For each chunk sizes (you want to evaluate), following steps are repeated:

- Create execution role for Knowledge Bases for Amazon Bedrock with necessary policies for accessing data from S3 and writing embeddings into vector store (OpenSearchServerless).
- Create an empty OpenSearch serverless index.
- Download documents (or point to your document S3 location)
- Create knowledge base for Amazon Bedrock 
- Create a data source within knowledge base which will connect to Amazon S3
- Once the data is available in the Bedrock Knowledge Bases with different chunk size, we'll evaluate the text chunks retreived for refernce QA pairs from these knowledge bases for faithfulness, correctness, and relevancy metrics using LlamaIndex. 
- Using these metrics we can decide for RIGHT chunk size for our RAG based application. 

Finally, based on the evaluation results, a question answering application with RIGHT chunk strategy can be built using the Amazon Bedrock APIs.  

***

### Note
If you use the notebook - `0_chunk_size_evaluation_for_KB_RAG.ipynb` for creating the knowledge bases and do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources. 

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description..
