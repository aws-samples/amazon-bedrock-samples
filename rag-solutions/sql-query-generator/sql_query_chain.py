from langchain.document_loaders import TextLoader
from langchain.embeddings import BedrockEmbeddings
from langchain.llms import Bedrock
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma

embeddings_model_id = "amazon.titan-embed-text-v1"
credentials_profile_name = "default"
region_name = "us-east-1"

bedrock_embedding = BedrockEmbeddings(
    credentials_profile_name=credentials_profile_name,
    region_name=region_name,
    model_id=embeddings_model_id
)

anthropic_claude_llm = Bedrock(
    credentials_profile_name=credentials_profile_name,
    region_name=region_name,
    model_id="anthropic.claude-v2"
)

TEMPLATE = """Given an input question, first create a syntactically correct SQLite query to run then return the query.
Make sure to use only existing columns and tables. Make sure to wrap table names with square brackets.
Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"

Answer the question based only on the following context:
{context}

Some examples of SQL queries that correspond to questions are:

-- Get subtotal for each order.
select OrderID, 
    format(sum(UnitPrice * Quantity * (1 - Discount)), 2) as Subtotal
from [Order Details]
group by OrderID
order by OrderID;

--For each employee, get their sales amount, broken down by country name.
select distinct b.*, a.CategoryName
from Categories a 
inner join Products b on a.CategoryID = b.CategoryID
where b.Discontinued = 0
order by b.ProductName;

-- Sales amount for each quarter excluding discounts
SELECT
  strftime('%Y', [OrderDate]) AS [Year],
  CASE
    WHEN CAST(strftime('%m', [OrderDate]) AS INTEGER) IN (1, 2, 3) THEN 'Q1'
    WHEN CAST(strftime('%m', [OrderDate]) AS INTEGER) IN (4, 5, 6) THEN 'Q2'
    WHEN CAST(strftime('%m', [OrderDate]) AS INTEGER) IN (7, 8, 9) THEN 'Q3'
    WHEN CAST(strftime('%m', [OrderDate]) AS INTEGER) IN (10, 11, 12) THEN 'Q4'
  END AS [Quarter],
  SUM([Quantity] * [UnitPrice] * (1 - [Discount])) AS [SalesAmount]
FROM [Order Details]
JOIN [Orders] ON [Order Details].[OrderID] = [Orders].[OrderID]
GROUP BY [Year], [Quarter]
ORDER BY [Year], [Quarter];


Question: {question}"""

custom_prompt_template = PromptTemplate(
    input_variables=["context", "question"], template=TEMPLATE
)

# Load the DDL document and split it into chunks
loader = TextLoader("northwind_ddl.sql")
documents = loader.load()

# Split document into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=0, separators=[" ", ",", "\n"]
)
docs = text_splitter.split_documents(documents)

# Load the embeddings into Chroma in-memory vector store
vectorstore = Chroma.from_documents(docs, embedding=bedrock_embedding)
vectorstore_retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

model = anthropic_claude_llm
prompt = ChatPromptTemplate.from_template(TEMPLATE)
chain = (
    {
        "context": vectorstore_retriever,
        "question": RunnablePassthrough()
    }
    | prompt
    | model
    | StrOutputParser()
)


def sql_chain(question):
    chain = (
        {
            "context": vectorstore_retriever,
            "question": RunnablePassthrough()
        }
        | prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke(question)
