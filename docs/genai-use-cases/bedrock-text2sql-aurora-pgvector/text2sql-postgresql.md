<h1>Text-to-SQL with Amazon Bedrock + PostgreSQL pgvector Aurora Serverless</h1>

**Keywords:** `text-to-sql` `amazon-bedrock` `postgresql-pgvector` `aurora-serverless` `claude-sonnet` `vector-database` `semantic-search` `aws-rds-data-api` `natural-language-sql` `llm-database-integration`

[![Open in GitHub](https://img.shields.io/badge/Open%20in-GitHub-blue?logo=github)](https://github.com/aws-samples/amazon-bedrock-samples)

This notebook demonstrates the integration of **traditional relational database operations** with **vector search capabilities** in PostgreSQL, featuring automated query strategy selection based on user intent analysis.

<h3>🎯 Core Technical Demonstrations:</h3>

#### 1. **Complex Schema Text-to-SQL Generation**

- LLM-powered natural language to SQL conversion across multi-table schemas
- Handling hierarchical data structures, complex joins, and nested aggregations
- **Demonstrating schema comprehension for enterprise-scale database architectures**

#### 2. **PostgreSQL pgvector Integration**

- Native vector storage and similarity search within PostgreSQL
- Embedding-based semantic search on unstructured text data
- Demonstrating RDBMS + vector database convergence

#### 3. **Automated Query Strategy Selection**

- Foundation model analysis of query intent and optimal execution path determination
- Context-aware routing between structured SQL and semantic vector operations
- Unified interface abstracting query complexity from end users

<h3>🏗️ Database Schema Architecture</h3>

ecommerce schema demonstrating complex relationships:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     users       │    │    categories    │    │    products     │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ user_id (PK)    │    │ category_id (PK) │    │ product_id (PK) │
│ email           │    │ name             │    │ sku             │
│ username        │    │ slug             │    │ name            │
│ first_name      │    │ description      │    │ description     │
│ last_name       │    │ parent_category_id│   │ category_id (FK)│
│ city            │    │   (FK to self)   │    │ brand           │
│ state_province  │    │ product_count    │    │ price           │
│ total_orders    │    └──────────────────┘    │ stock_quantity  │
│ total_spent     │           │                │ rating_average  │
└─────────────────┘           │                │ total_sales     │
         │                    │                │ revenue_generated│
         │                    │                └─────────────────┘
         │                    │                         │
         │                    │                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     orders      │    │   order_items    │    │    reviews      │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ order_id (PK)   │────│ order_id (FK)    │    │ review_id (PK)  │
│ order_number    │    │ product_id (FK)  │────│ product_id (FK) │
│ user_id (FK)    │    │ quantity         │    │ user_id (FK)    │
│ order_status    │    │ unit_price       │    │ order_id (FK)   │
│ payment_status  │    │ total_price      │    │ rating          │
│ total_amount    │    └──────────────────┘    │ title           │
│ shipping_method │                            │ comment         │
│ created_at      │                            │ comment_embedding│
└─────────────────┘                            │   (VECTOR)      │
                                               │ pros            │
                                               │ cons            │
                                               └─────────────────┘
```

**Schema Complexity Features:**

- **Self-referencing hierarchies**: Categories with parent/child relationships
- **Junction table patterns**: Many-to-many order-product relationships via order_items
- **Vector integration**: Native pgvector storage in reviews.comment_embedding
- **Multi-level foreign keys**: Reviews referencing users, products, and orders

<h3>💡 Technical Implementation:</h3>

1. **Hybrid Database Architecture**: PostgreSQL with pgvector extension for unified structured + vector operations
2. **LLM Schema Comprehension**: Foundation model understanding of complex table relationships and optimal query generation
3. **Embedding-based Similarity**: Amazon Titan text embeddings for semantic content matching
4. **Automated Tool Selection**: Context analysis determining SQL vs vector search execution paths

## Technical Prerequisites

- AWS account with Bedrock and RDS permissions
- Understanding of vector embeddings and similarity search concepts
- Familiarity with PostgreSQL and complex SQL operations

---

<h2>📦 STEP 1: Install Required Packages</h2>

```python
# Install required Python packages for AWS and SQL parsing
!pip install --upgrade pip
!pip install boto3 sqlparse
```

<h2>🏗️ STEP 2: Deploy AWS Infrastructure</h2>

This step creates:

- **VPC with 3 subnets** across availability zones
- **Aurora PostgreSQL Serverless v2 cluster** with HTTP endpoint enabled
- **Security groups** and networking configuration
- **Secrets Manager** for database credentials

**Note**: This takes ~5-10 minutes to complete

```python
# Deploy AWS infrastructure (VPC, Aurora PostgreSQL, Security Groups)
# This script creates all necessary AWS resources for our demo

!python infra.py
```

<h2>🔧 STEP 3: Setup Database Connection</h2>

```python
# Import required libraries for AWS services and database operations
import json
import boto3
import logging
import sqlparse
from typing import Dict, Any, List, Union
from botocore.exceptions import ClientError
from botocore.config import Config

# Get current AWS region dynamically
session = boto3.Session()
AWS_REGION = session.region_name or 'us-west-2'  # fallback to us-west-2 if not set
print(f"Using AWS region: {AWS_REGION}")

# Setup logging to track our progress
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
```

```python
# Database connection configuration
# **Update these values after running infra.py with the output provided**
CLUSTER_ARN = ''
SECRET_ARN = ''
DATABASE_NAME = ''
AWS_REGION = ''

# Initialize RDS Data API client (allows SQL execution without direct connections, to learn more visit https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html)
rds_client = boto3.client('rds-data', region_name=AWS_REGION)
```

<h2>🛠️ STEP 4: Create Database Schema & Load Data</h2>

We'll create a streamlined but complex ecommerce schema with 6 core tables that demonstrate:

- **Hierarchical relationships** (categories with parent/child structure)
- **Many-to-many relationships** (orders ↔ products via junction table)
- **Vector integration** (reviews with embedding column for semantic search)
- **Analytics capabilities** (aggregated sales metrics and customer data)

```python
def run_sql(query: str, database: str = None) -> dict:
    """
    Execute SQL query using RDS Data API
    This is our main function for running any SQL command
    """
    try:
        params = {
            'resourceArn': CLUSTER_ARN,
            'secretArn': SECRET_ARN,
            'sql': query
        }
        if database:
            params['database'] = database

        response = rds_client.execute_statement(**params)
        return response
    except Exception as e:
        print(f"SQL execution error: {e}")
        return {"error": str(e)}
```

```python
# Enable pgvector extension for semantic search capabilities
# pgvector allows PostgreSQL to store and search vector embeddings
try:
    result = run_sql('CREATE EXTENSION IF NOT EXISTS vector;', DATABASE_NAME)
    print("✅ pgvector extension enabled successfully")
except Exception as e:
    print(f"Extension setup error: {e}")
```

```python
# Create tables by reading our schema file
# Parse SQL file into individual statements (RDS Data API requirement)
with open('ecommerce_schema.sql', 'r') as f:
    schema_sql = f.read()

statements = sqlparse.split(schema_sql)
statements = [stmt.strip() for stmt in statements if stmt.strip()]

print(f"Creating {len(statements)} database tables...")
print("📊 Schema includes: users, categories, products, orders, order_items, reviews")
print("🧠 Vector integration: reviews.comment_embedding for semantic search")

# Execute each CREATE TABLE statement
for i, statement in enumerate(statements, 1):
    try:
        run_sql(statement, DATABASE_NAME)
        print(f"  ✅ Table {i} created successfully")
    except Exception as e:
        print(f"  ❌ Table {i} failed: {e}")

print("✅ Database schema creation completed!")
```

```python
# Insert sample data into our tables
with open('ecommerce_data.sql', 'r') as f:
    data_sql = f.read()

data_statements = sqlparse.split(data_sql)
data_statements = [stmt.strip() for stmt in data_statements if stmt.strip()]

print(f"Inserting sample data with {len(data_statements)} statements...")
print("👥 15 users across different US cities with spending history")
print("📦 16 products across 8 categories (Electronics → Audio/Video, Smart Devices, etc.)")
print("🛒 10 orders with various statuses (delivered, shipped, processing, cancelled)")
print("⭐ 13 detailed product reviews perfect for semantic search")

for i, statement in enumerate(data_statements, 1):
    try:
        result = run_sql(statement, DATABASE_NAME)
        records_affected = result.get('numberOfRecordsUpdated', 0)
        print(f"  ✅ Dataset {i}: {records_affected} records inserted")
    except Exception as e:
        print(f"  ❌ Dataset {i} failed: {e}")

print("✅ Sample data insertion completed!")
```

<h2>🧠 STEP 5: Bedrock Setup</h2>

```python
# Configure Bedrock client with extended timeouts for large requests
bedrock_config = Config(
    connect_timeout=60*5,  # 5 minutes
    read_timeout=60*5,     # 5 minutes
)

bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=AWS_REGION,
    config=bedrock_config
)

# Model IDs for our use
CLAUDE_MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # For text-to-SQL
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"                # For vector search

print("✅ Bedrock configured successfully")
```

```python
class DatabaseTools:
    """Simple database helper for executing SQL queries"""

    def __init__(self):
        self.rds_client = boto3.client("rds-data", region_name=AWS_REGION)

    def execute_sql(self, query: str) -> str:
        """Execute SQL query and return results as JSON string"""
        try:
            response = self.rds_client.execute_statement(
                resourceArn=CLUSTER_ARN,
                secretArn=SECRET_ARN,
                database=DATABASE_NAME,
                sql=query,
                includeResultMetadata=True,
            )

            # Handle empty results
            if "records" not in response or not response["records"]:
                return json.dumps([])

            # Get column names and format results
            columns = [field["name"] for field in response.get("columnMetadata", [])]
            results = []

            for record in response["records"]:
                row_values = []
                for field in record:
                    # Extract value from different field types
                    if "stringValue" in field:
                        row_values.append(field["stringValue"])
                    elif "longValue" in field:
                        row_values.append(field["longValue"])
                    elif "doubleValue" in field:
                        row_values.append(field["doubleValue"])
                    elif "booleanValue" in field:
                        row_values.append(field["booleanValue"])
                    else:
                        row_values.append(None)

                results.append(dict(zip(columns, row_values)))

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": f"Database error: {str(e)}"})

# Test database connection
db_tools = DatabaseTools()
result = db_tools.execute_sql("SELECT current_timestamp;")
print("✅ Database connection test successful")
print("Current time:", json.loads(result)[0]["current_timestamp"])
```

<h2>🔢 STEP 6: Generate Vector Embeddings for Semantic Search</h2>

**Hybrid RDBMS + Vector Database Implementation:**

Vector embeddings convert textual content into high-dimensional numerical representations that capture semantic relationships. PostgreSQL's pgvector extension enables native vector operations within the relational database, eliminating the need for separate vector database infrastructure.

**Technical Implementation:**

- Amazon Titan Text Embeddings v2 (1024-dimensional vectors)
- PostgreSQL VECTOR data type with cosine similarity operations
- Semantic search on review content independent of exact keyword matching

This approach demonstrates the convergence of traditional RDBMS and vector database capabilities in production systems.

```python
def create_embedding(text: str) -> List[float]:
    """
    Convert text into a vector embedding using Amazon Titan
    Returns a list of 1024 numbers that represent the text's meaning
    """
    payload = {
        "inputText": text,
        "embeddingTypes": ["float"]
    }

    try:
        response = bedrock.invoke_model(
            modelId=EMBEDDING_MODEL,
            body=json.dumps(payload),
            accept="application/json",
            contentType="application/json"
        )

        body = json.loads(response["body"].read())
        embeddings = body.get("embeddingsByType", {}).get("float", [])
        return embeddings

    except Exception as e:
        print(f"Embedding generation error: {e}")
        return []

# Test embedding generation
test_text = "This battery lasts a long time"
test_embedding = create_embedding(test_text)
print(f"✅ Generated embedding with {len(test_embedding)} dimensions")
print(f"Sample values: {test_embedding[:5]}...")  # Show first 5 numbers
```

```python
def add_embeddings_to_reviews():
    """
    Generate embeddings for all review comments and store them in the database
    This enables semantic search on review content
    """

    # Step 1: Find reviews that need embeddings
    count_query = "SELECT COUNT(*) FROM reviews WHERE comment_embedding IS NULL"
    count_result = db_tools.execute_sql(count_query)
    total_missing = json.loads(count_result)[0]["count"]

    print(f"Found {total_missing} reviews needing embeddings")

    if total_missing == 0:
        print("✅ All reviews already have embeddings!")
        return

    # Step 2: Get reviews without embeddings
    select_query = """
        SELECT review_id, comment
        FROM reviews
        WHERE comment_embedding IS NULL
        AND comment IS NOT NULL
        ORDER BY review_id
    """

    result = db_tools.execute_sql(select_query)
    reviews = json.loads(result)

    # Step 3: Generate embeddings for each review
    for review in reviews:
        review_id = review["review_id"]
        comment = review["comment"]

        if not comment:
            continue

        print(f"  Processing review {review_id}...")

        # Generate embedding
        embedding = create_embedding(comment)
        if not embedding:
            continue

        # Convert to PostgreSQL vector format
        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Update database with embedding
        update_query = f"""
            UPDATE reviews
            SET comment_embedding = '{vector_str}'::vector
            WHERE review_id = {review_id}
        """

        run_sql(update_query, DATABASE_NAME)
        print(f"    ✅ Added embedding for review {review_id}")

    print("✅ All review embeddings generated successfully!")

# Generate embeddings for all reviews
add_embeddings_to_reviews()
```

<h2>🤖 STEP 7: Foundation Model Tool Selection System</h2>

**Query Strategy Determination:**

Claude Sonnet analyzes natural language queries and automatically determines the optimal execution strategy through tool selection logic:

**📊 Structured Query Scenarios (SQL Tool Selection):**

- Aggregation operations: "What's the average order value by state?"
- Complex joins: "Show customers with repeat purchases in Electronics"
- Mathematical calculations: "Calculate profit margins by product category"
- Temporal analysis: "Find order trends over the last quarter"

**🔍 Semantic Search Scenarios (Vector Tool Selection):**

- Content similarity: "Find reviews about build quality issues"
- Sentiment analysis: "Show complaints about customer service"
- Topic clustering: "What do users say about product durability?"
- Conceptual matching: Independent of exact keyword presence

**🎯 Hybrid Query Execution:**

- Complex scenarios may trigger multiple tool usage
- Foundation model orchestrates sequential or parallel execution
- Results synthesis from both structured and semantic operations

**Technical Architecture:**

- Tool specification via JSON schema definitions
- Automated function calling based on intent classification
- Context-aware execution path optimization

```python
def semantic_search(search_text: str, limit: int = 5) -> str:
    """
    Find reviews similar to the search text using vector similarity
    Returns the most semantically similar reviews
    """
    try:
        # Generate embedding for search text
        search_embedding = create_embedding(search_text)
        if not search_embedding:
            return json.dumps({"error": "Could not generate embedding"})

        # Convert to PostgreSQL vector format
        vector_str = "[" + ",".join(str(x) for x in search_embedding) + "]"

        # Find similar reviews using cosine distance (<-> operator)
        query = f"""
        SELECT
            rating,
            title,
            comment,
            pros,
            cons,
            helpful_count,
            (1 - (comment_embedding <-> '{vector_str}'::vector)) as similarity_score
        FROM reviews
        WHERE comment IS NOT NULL
        AND comment_embedding IS NOT NULL
        ORDER BY comment_embedding <-> '{vector_str}'::vector
        LIMIT {limit}
        """

        result = db_tools.execute_sql(query)
        return result

    except Exception as e:
        return json.dumps({"error": f"Vector search error: {str(e)}"})

# Test vector search
test_search = semantic_search("battery problems", limit=3)
print("✅ Vector search test successful")
print("Sample results:", json.loads(test_search)[0]["title"] if json.loads(test_search) else "No results")
```

```python
# Define the tools available to Claude
TOOLS = {
    "tools": [
        {
            "toolSpec": {
                "name": "execute_sql",
                "description": "Execute SQL queries for structured data analysis (counts, filters, joins, aggregations)",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute against the ecommerce database"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "vector_search",
                "description": "Perform semantic similarity search on review content to find similar topics/themes",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to search for semantically similar content in reviews"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        }
    ],
    "toolChoice": {"auto": {}}
}

print("✅ AI tools configured - Claude can now choose between SQL and vector search!")
```

````python
SYSTEM_PROMPT = """
# Advanced Text-to-SQL System Prompt with PostgreSQL Vector Search

<role>
You are an advanced database query optimization system specializing in hybrid SQL and vector search operations.
Your primary function is to analyze natural language queries, determine optimal execution strategies, and generate PostgreSQL queries that leverage both relational and vector capabilities.
</role>

<schema>

<table name="users">
<purpose>
Customer profiles with pre-computed analytics for performance optimization
</purpose>
<key_columns>
- user_id (SERIAL PRIMARY KEY)
- email, username (UNIQUE constraints for data integrity)
- first_name, last_name, phone_number, date_of_birth, gender
- city, state_province, country_code (geographic segmentation)
- account_status (operational flag)
- total_orders, total_spent (denormalized aggregates for fast analytics)
- created_at (temporal tracking)
</key_columns>
</table>

<table name="categories">
<purpose>
Hierarchical product taxonomy with recursive relationship support
</purpose>
<key_columns>
- category_id (SERIAL PRIMARY KEY)
- name, slug (unique URL-safe identifier), description
- parent_category_id (SELF-REFERENTIAL FK enabling tree structures)
- is_active (soft delete support)
- product_count (denormalized for performance)
- created_at
</key_columns>
</table>

<table name="products">
<purpose>
Product catalog with inventory tracking and performance metrics
</purpose>
<key_columns>
- product_id (SERIAL PRIMARY KEY)
- sku (UNIQUE business identifier)
- name, slug, description, short_description
- category_id (FK to categories)
- brand, price, cost (profit margin calculation)
- weight_kg, stock_quantity (logistics data)
- is_active, is_featured (display control)
- warranty_months
- rating_average, rating_count (computed from reviews)
- total_sales, revenue_generated (business metrics)
- created_at, updated_at (audit trail)
</key_columns>
</table>

<table name="orders">
<purpose>
Transaction lifecycle management with comprehensive status tracking
</purpose>
<key_columns>
- order_id (SERIAL PRIMARY KEY)
- order_number (UNIQUE human-readable identifier)
- user_id (FK to users)
- order_status: pending|processing|shipped|delivered|cancelled|refunded
- payment_status: pending|paid|failed|refunded
- shipping_address (full text for flexibility)
- financial_breakdown:
  * subtotal (items before adjustments)
  * tax_amount, shipping_cost, discount_amount
  * total_amount (final charge)
- payment_method: credit_card|paypal|bank_transfer
- shipping_method: standard|express|overnight
- customer_notes, tracking_number
- shipped_at, delivered_at (fulfillment tracking)
- created_at, updated_at
</key_columns>
</table>

<table name="order_items">
<purpose>
Junction table capturing point-in-time pricing and item-level details
</purpose>
<key_columns>
- order_item_id (SERIAL PRIMARY KEY)
- order_id (FK CASCADE DELETE)
- product_id (FK)
- quantity, unit_price (historical pricing preservation)
- discount_amount, tax_amount (item-level adjustments)
- total_price (computed line total)
- created_at
</key_columns>
</table>

<table name="reviews">
<purpose>
Customer feedback with vector embeddings for semantic analysis
</purpose>
<key_columns>
- review_id (SERIAL PRIMARY KEY)
- product_id (FK CASCADE DELETE)
- user_id (FK)
- order_id (FK optional - links to purchase)
- rating (INTEGER CHECK 1-5)
- title (VARCHAR(200))
- comment (TEXT - source for embeddings)
- comment_embedding (VECTOR(1024) - semantic representation)
- pros, cons (structured sentiment extraction)
- is_verified_purchase (trust signal)
- helpful_count (community validation)
- status: pending|approved|rejected
- created_at, updated_at
</key_columns>
<vector_capabilities>
- comment_embedding enables semantic similarity search
- Cosine distance for finding related reviews
- Supports sentiment clustering and topic modeling
</vector_capabilities>
</table>
</schema>

<tool_selection>
**execute_sql**: Use for structured queries, aggregations, joins, filtering by exact values

**vector_search**: Use for semantic similarity on review comments, finding related content

Examples:
- "total revenue by category" → execute_sql
- "reviews similar to 'great battery life'" → vector_search
- "average rating of products with positive reviews" → both tools
</tool_selection>

<query_patterns>
SQL Example:
```sql
SELECT c.name, SUM(p.revenue_generated) as revenue
FROM categories c
JOIN products p ON c.category_id = p.category_id
GROUP BY c.name
ORDER BY revenue DESC;
````

Vector Example:

```sql
-- Note: query_embedding would be provided by the system as a VECTOR(1024)
SELECT r.comment, p.name,
       r.comment_embedding <=> query_embedding as similarity
FROM reviews r
JOIN products p ON r.product_id = p.product_id
ORDER BY similarity
LIMIT 5;
```

</query_patterns>

### SQL Query Best Practices

<sql_requirements>

1. **Explicit JOINs**: Always use explicit JOIN syntax with ON conditions
2. **Table Aliases**: Use meaningful aliases (u for users, p for products)
3. **NULL Handling**: Account for optional fields with COALESCE or IS NULL
4. **Data Types**: Cast when necessary, especially for date operations
5. **Aggregation Rules**: Include all non-aggregate columns in GROUP BY
6. **Order Stability**: Add secondary ORDER BY for deterministic results
7. **Limit Appropriately**: Include LIMIT for top-N queries
8. **Comment Complex Logic**: Add -- comments for CTEs or complex conditions
   </sql_requirements>

### Vector Search Best Practices

<vector_requirements>

1. **Distance Metrics**: Use cosine distance (<=>) for normalized embeddings
2. **Result Limits**: Always limit results (default 10-20 for readability)
3. **Threshold Filtering**: Consider similarity threshold for quality control
4. **Metadata Inclusion**: Join with products/users for context
5. **Explain Similarity**: Include distance scores in results
   </vector_requirements>

<output_format>

### Response Structure

```
QUERY ANALYSIS:
- Intent: [Extracted user intent]
- Strategy: [Selected tool(s) and rationale]
- Key Operations: [Main database operations required]

GENERATED QUERY:
[Actual SQL or vector search syntax]

EXPECTED INSIGHTS:
- [Key patterns or metrics the query will reveal]
- [Business value of the results]
```

</output_format>
"""

````


```python
def ask_ai(question: str) -> str:
    """
    Send a question to Claude and handle tool execution
    Claude will automatically choose between SQL and vector search
    Handles multiple rounds of tool calls until completion
    """

    # Create the conversation
    messages = [{"role": "user", "content": [{"text": question}]}]

    try:
        # Continue conversation until Claude stops requesting tools
        max_turns = 10  # Prevent infinite loops
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1

            # Send to Claude with tools
            response = bedrock.converse(
                modelId=CLAUDE_MODEL,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                toolConfig=TOOLS
            )

            assistant_message = response["output"]["message"]
            messages.append(assistant_message)

            # Check if Claude wants to use tools
            tool_uses = [content for content in assistant_message["content"] if "toolUse" in content]

            if tool_uses:
                # Execute each tool Claude requested
                for tool_use in tool_uses:
                    tool_name = tool_use["toolUse"]["name"]
                    tool_input = tool_use["toolUse"]["input"]
                    tool_id = tool_use["toolUse"]["toolUseId"]

                    print(f"🔧 Claude is using: {tool_name}")

                    # Execute the appropriate tool
                    if tool_name == "execute_sql":
                        tool_result = db_tools.execute_sql(tool_input["query"])
                        print(f"📊 SQL Query: {tool_input['query']}")

                    elif tool_name == "vector_search":
                        tool_result = semantic_search(tool_input["text"])
                        print(f"🔍 Searching for: {tool_input['text']}")

                    # Send tool result back to Claude
                    tool_message = {
                        "role": "user",
                        "content": [{
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"text": tool_result}]
                            }
                        }]
                    }
                    messages.append(tool_message)

                # Continue the loop to let Claude process results and potentially make more tool calls
                continue

            else:
                # No tools needed, extract and return the final response
                final_content = assistant_message["content"]
                text_response = next((c["text"] for c in final_content if "text" in c), "")
                return text_response

        # If we hit max turns, return what we have
        return "Response completed after maximum tool execution rounds."

    except Exception as e:
        return f"Error: {str(e)}"

print("✅ Enhanced LLM assistant ready with multi-round tool execution support!")
````

<h2>🚀 STEP 8: Technical Demonstrations</h2>

<h3>Demo 1: Complex Schema Text-to-SQL Generation</h3>
**Objective:** Validate LLM comprehension of multi-table relationships and automated SQL generation for complex analytical queries.

```python
# DEMO 1: Complex Schema Text-to-SQL Generation
print("=" * 70)
print("DEMO 1: Complex Schema Text-to-SQL Generation")
print("=" * 70)

# Test multi-table join with hierarchical traversal and aggregation
question1 = "Show me the top 3 customers by total spending, including their order count and favorite product category"
print(f"Query: {question1}")
print("\n🔧 Expected: Multi-table JOIN across users, orders, order_items, products, categories")
print("\nExecution:")
answer1 = ask_ai(question1)
print(answer1)
print("\n" + "="*70)
```

<h3>Demo 2: PostgreSQL Vector Search Implementation</h3>
**Objective:** Demonstrate native vector operations within PostgreSQL using pgvector for semantic similarity search on unstructured content.

```python
# DEMO 2: PostgreSQL Vector Search Implementation
print("DEMO 2: PostgreSQL Vector Search Implementation")
print("=" * 70)

question2 = "Find reviews about battery life issues and charging problems"
print(f"Query: {question2}")
print("\n🔧 Expected: Vector similarity search using pgvector cosine distance")
print("📊 Operation: Embedding generation + semantic matching on reviews.comment_embedding")
print("🎯 Capability: Content similarity independent of exact keyword presence")
print("\nExecution:")
answer2 = ask_ai(question2)
print(answer2)
print("\n" + "="*70)
```

<h3>Demo 3: Automated Query Strategy Selection</h3>
**Objective:** Capability to analyze query intent and select optimal execution strategy between SQL and vector operations.

```python
# DEMO 3: Automated Query Strategy Selection
print("DEMO 3: Automated Query Strategy Selection")
print("=" * 70)

# Ambiguous query that could use either approach
question3 = "What are the main product quality issues customers mention in their reviews?"
print(f"Query: {question3}")
print("\n🤔 Strategy Options:")
print("   📊 SQL Approach: Aggregate review ratings and identify low-rated products")
print("   🔍 Vector Approach: Semantic search for quality-related content themes")
print("   🎯 Hybrid Approach: Combine structured filtering with content analysis")
print("\n🔧 Foundation Model Decision Process:")
print("\nExecution:")
answer3 = ask_ai(question3)
print(answer3)
print("\n" + "="*70)
```

<h2>💬 Interactive Query Testing</h2>

**Technical Validation Environment**

Test the foundation model's query strategy selection across different analytical scenarios. The system will demonstrate automated tool selection based on query characteristics and optimal execution path determination.

**Structured Query Test Cases:**

**📊 Complex SQL Operations:**

- "Calculate profit margins by hierarchical product category"
- "Identify customers with highest purchase frequency in Texas"
- "Analyze order value distribution across payment methods"

**🔍 Vector Similarity Operations:**

- "Find reviews discussing build quality and manufacturing defects"
- "Locate customer feedback about shipping and logistics issues"
- "Identify content related to product longevity and durability concerns"
- "Search for mentions of value proposition and pricing feedback"

**🎯 Complex Analytical Scenarios:**

- "Which products receive the most quality-related complaints?"
- "Analyze sentiment patterns across different customer segments"
- "Find correlation between product price points and satisfaction themes"

```python
# Interactive Query Testing Environment
print("🔧 Foundation Model Query Strategy Testing")
print("Enter queries to validate automated tool selection logic. Type 'quit' to exit.")
print("\n📋 Test Categories:")

print("\n📊 Structured Data Operations:")
print("• 'Which product categories have the highest profit margins?'")
print("• 'Show customer geographic distribution by total spending'")
print("• 'Analyze order completion rates by shipping method'")

print("\n🔍 Semantic Content Analysis:")
print("• 'Find reviews about products being difficult to use or setup'")
print("• 'Locate feedback about customer support experiences'")
print("• 'Search for mentions of product packaging and presentation'")

print("\n🎯 Hybrid Analysis Scenarios:")
print("• 'Identify top-selling products with usability complaints'")
print("• 'Find high-value customers who mention quality concerns'")

print("-" * 70)

while True:
    question = input("\n🔍 Query: ").strip()

    if question.lower() == 'quit':
        print("✅ Query testing session completed")
        break

    if question:
        print(f"\n📝 Processing: {question}")
        print("⚙️  Analyzing query intent and determining execution strategy...")
        answer = ask_ai(question)
        print(f"\n📊 Result: {answer}")
        print("-" * 70)
```

<h2>🧹 STEP 9: Cleanup (Optional)</h2>
Run this to delete all AWS resources and avoid charges

```python
# Cleanup AWS resources to avoid ongoing charges
# This will delete the Aurora cluster, VPC, and all related resources

# Primary method:
!python clean.py
```

---

<h2>🔍 Tags</h2>

`#text-to-sql` `#amazon-bedrock` `#postgresql-pgvector` `#aurora-serverless` `#claude-sonnet` `#vector-database` `#semantic-search` `#aws-rds-data-api` `#natural-language-sql` `#llm-database-integration` `#enterprise-ai` `#hybrid-database` `#sql-generation` `#vector-similarity` `#bedrock-integration`
