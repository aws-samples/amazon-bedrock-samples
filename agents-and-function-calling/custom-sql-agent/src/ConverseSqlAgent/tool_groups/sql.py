import io
import csv
import json
import boto3
from sqlalchemy import create_engine, text, inspect

import boto3
import json
from botocore.exceptions import ClientError

def retrieve_database_url(secrets_manager_key, database_name=None):
    """
    Returns a URL for SQLAlchemy based on AWS Secrets Manager credentials.

    Args:
        secrets_manager_key (str): The AWS Secrets Manager key for the connection details.
        database_name (str, optional): The name of the database to connect to. If specified,
            this will override the database name from secrets manager.

    Returns:
        str: A SQLAlchemy URL.

    Raises:
        ValueError: If required credentials are missing or if the engine is not supported.
        boto3.exceptions.Boto3Error: If there's an issue with the AWS SDK.
        json.JSONDecodeError: If the secret string is not valid JSON.
        ClientError: If there's an error in retrieving the secret from AWS Secrets Manager.
    """
    try:
        # Retrieve secrets from AWS Secrets Manager
        secrets_manager = boto3.client('secretsmanager')
        try:
            secret_response = secrets_manager.get_secret_value(SecretId=secrets_manager_key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise ValueError(f"The specified secret {secrets_manager_key} was not found") from e
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                raise ValueError(f"The request had invalid params: {e}") from e
            else:
                raise

        # Parse the secret string
        try:
            secret = json.loads(secret_response['SecretString'])
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON in secret string") from e

        # Extract database credentials
        username = secret.get('username')
        password = secret.get('password')
        host = secret.get('host')
        port = secret.get('port')
        engine = secret.get('engine')
        database = database_name or secret.get('database')

        # Validate required credentials
        required_fields = ['username', 'password', 'host', 'port', 'engine']
        missing_fields = [field for field in required_fields if not secret.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required credentials: {', '.join(missing_fields)}")

        # Map engine to dialect_driver
        engine_map = {
            "postgres": "postgresql",
            "mysql": "mysql+pymysql",
            "mssql": "mssql+pyodbc",
            # Add more engines as needed
        }
        dialect_driver = engine_map.get(engine)
        if not dialect_driver:
            raise ValueError(f"Unsupported engine: {engine}")

        # Build the database URL
        url = f"{dialect_driver}://{username}:{password}@{host}:{port}"
        # If a database is specified, append it to the URL
        if database:
            url += f"/{database}"
        return url

    except boto3.exceptions.Boto3Error as e:
        raise ValueError(f"Error with AWS SDK: {str(e)}") from e

def invoke_sql_query(self, secrets_manager_key, database_name, query):
    """
    Invokes a SQL query against a database.

    Args:
        secrets_manager_key (str): The Secrets Manager Key to retrieve connection details.
        database_name (str): The name of the database to connect to.
        query (str): The SQL statement to execute.

    Returns:
        str: A CSV string of the SQL execution output.
    """
    try:
        url = retrieve_database_url(secrets_manager_key, database_name)
        engine = create_engine(url)
        with engine.connect() as connection:
            result = connection.execute(text(query))
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(result.keys())
        writer.writerows(result)
        final_output = output.getvalue()
    except Exception as e:
        final_output = f"Invoking SQL query encountered an error: {e}"
    return final_output

def get_database_schemas(self, secrets_manager_key, database_name):
    """
    Retrieves a list of schemas in a database.

    Args:
        secrets_manager_key (str): The Secrets Manager Key to retrieve connection details.
        database_name (str): The name of the database to connect to.

    Returns:
        str: A CSV string of the database schemas.
    """
    try:
        url = retrieve_database_url(secrets_manager_key, database_name)
        engine = create_engine(url)
        inspector = inspect(engine)
        schemas = inspector.get_schema_names()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Schema"])
        for schema in schemas:
            writer.writerow([schema])
        final_output = output.getvalue()
    except Exception as e:
        final_output = f"Getting database schemas encountered an error: {e}"
    return final_output

def get_schema_tables(self, secrets_manager_key, database_name, schema):
    """
    Retrieves a list of tables in a specific schema.

    Args:
        secrets_manager_key (str): The Secrets Manager Key to retrieve connection details.
        database_name (str): The name of the database to connect to.
        schema (str): The name of the schema to get tables from.

    Returns:
        str: A CSV string of the tables in the specified schema.
    """
    try:
        url = retrieve_database_url(secrets_manager_key, database_name)
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names(schema=schema)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Table"])
        for table in tables:
            writer.writerow([table])
        final_output = output.getvalue()
    except Exception as e:
        final_output = f"Getting schema tables encountered an error: {e}"
    return final_output

def get_table_columns(self, secrets_manager_key, database_name, schema, table):
    """
    Retrieves a list of columns and their properties for a specific table in a schema.

    Args:
        secrets_manager_key (str): The Secrets Manager Key to retrieve connection details.
        database_name (str): The name of the database to connect to.
        schema (str): The name of the schema containing the table.
        table (str): The name of the table to get columns from.

    Returns:
        str: A CSV string of the columns in the specified table.
    """
    try:
        url = retrieve_database_url(secrets_manager_key, database_name)
        engine = create_engine(url)
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name=table, schema=schema)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Column Name", "Data Type", "Nullable", "Default", "Primary Key"])
        for column in columns:
            writer.writerow([
                column['name'],
                str(column['type']),
                str(column.get('nullable', '')),
                str(column.get('default', '')),
                str(column.get('primary_key', False))
            ])
        final_output = output.getvalue()
    except Exception as e:
        final_output = f"Getting table columns encountered an error: {e}"
    return final_output

def get_foreign_keys(self, secrets_manager_key, database_name, schema=None):
    """
    Retrieves foreign key relationships in a database.

    Args:
        secrets_manager_key (str): The Secrets Manager Key to retrieve connection details.
        database_name (str): The name of the database to connect to.
        schema (str, optional): The name of the schema to get foreign keys from. If None, gets from all schemas.

    Returns:
        str: A CSV string of the foreign key relationships.
    """
    try:
        url = retrieve_database_url(secrets_manager_key, database_name)
        engine = create_engine(url)
        inspector = inspect(engine)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Schema", "Table", "Column", "Foreign Schema", "Foreign Table", "Foreign Column"])

        if schema:
            schemas = [schema]
        else:
            schemas = inspector.get_schema_names()

        for schema_name in schemas:
            for table_name in inspector.get_table_names(schema=schema_name):
                fks = inspector.get_foreign_keys(table_name, schema=schema_name)
                for fk in fks:
                    writer.writerow([
                        schema_name,
                        table_name,
                        fk['constrained_columns'][0],
                        fk.get('referred_schema', schema_name),
                        fk['referred_table'],
                        fk['referred_columns'][0]
                    ])

        final_output = output.getvalue()
    except Exception as e:
        final_output = f"Getting foreign keys encountered an error: {e}"

    return final_output

# New ToolSpec for get_foreign_keys
GET_FOREIGN_KEYS_TOOLSPEC = {
    "toolSpec": {
        "name": "get_foreign_keys",
        "description": "Use this tool to get foreign key relationships in a database",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "secrets_manager_key": {
                        "type": "string",
                        "description": "Enter the AWS Secrets Manager key that will be used for the database server connection"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "The name of the database to connect to in the server"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Optional. The name of the schema to get foreign keys from. If not provided, gets from all schemas."
                    }
                },
                "required": ["secrets_manager_key", "database_name"]
            }
        }
    }
}


# ToolSpecs

INVOKE_SQL_TOOLSPEC = {
    "toolSpec": {
        "name": "invoke_sql_query",
        "description": "Use this tool to invoke a SQL query against a database",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "secrets_manager_key": {
                        "type": "string",
                        "description": "Enter the AWS Secrets Manager key that will be used for the database server connection"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "The name of the database to connect to in the server"
                    },
                    "query": {
                        "type": "string",
                        "description": "This is a SQL query that is valid to the database"
                    }
                },
                "required": ["secrets_manager_key", "database_name", "query"]
            }
        }
    }
}

GET_DATABASE_SCHEMAS_TOOLSPEC = {
    "toolSpec": {
        "name": "get_database_schemas",
        "description": "Use this tool to get a list of schemas in a database",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "secrets_manager_key": {
                        "type": "string",
                        "description": "Enter the AWS Secrets Manager key that will be used for the database server connection"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "The name of the database to connect to in the server"
                    }
                },
                "required": ["secrets_manager_key", "database_name"]
            }
        }
    }
}

GET_SCHEMA_TABLES_TOOLSPEC = {
    "toolSpec": {
        "name": "get_schema_tables",
        "description": "Use this tool to get a list of tables in a specific schema",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "secrets_manager_key": {
                        "type": "string",
                        "description": "Enter the AWS Secrets Manager key that will be used for the database server connection"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "The name of the database to connect to in the server"
                    },
                    "schema": {
                        "type": "string",
                        "description": "This is the name of the schema to get tables from."
                    }
                },
                "required": ["secrets_manager_key", "database_name", "schema"]
            }
        }
    }
}

GET_TABLE_COLUMNS_TOOLSPEC = {
    "toolSpec": {
        "name": "get_table_columns",
        "description": "Use this tool to get a list of columns and their properties for a specific table in a schema",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "secrets_manager_key": {
                        "type": "string",
                        "description": "Enter the AWS Secrets Manager key that will be used for the database server connection"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "The name of the database to connect to in the server"
                    },
                    "schema": {
                        "type": "string",
                        "description": "This is the name of the schema containing the table."
                    },
                    "table": {
                        "type": "string",
                        "description": "This is the name of the table to get columns from."
                    }
                },
                "required": ["secrets_manager_key", "database_name", "schema", "table"]
            }
        }
    }
}

# Update SQL_TOOL_GROUP to include the new tool
SQL_TOOL_GROUP = {
    "tool_group_name": "SQL_TOOL_GROUP",
    "usage_instructions": """Always try to use more specific SQL tools first before using invoke_sql_query.
    Check your memory first for any data dictionary that you may have built already. If you don't find it
    in your memory, then query the database. Unless the user has specifically asked for the SQL query,
    ensure that you provide the final answer in natural language after executing the query. 
    """,
    "tools": [
        {
            "tool_spec": INVOKE_SQL_TOOLSPEC,
            "function": invoke_sql_query
        },
        {
            "tool_spec": GET_DATABASE_SCHEMAS_TOOLSPEC,
            "function": get_database_schemas
        },
        {
            "tool_spec": GET_SCHEMA_TABLES_TOOLSPEC,
            "function": get_schema_tables
        },
        {
            "tool_spec": GET_TABLE_COLUMNS_TOOLSPEC,
            "function": get_table_columns
        },
        {
            "tool_spec": GET_FOREIGN_KEYS_TOOLSPEC,
            "function": get_foreign_keys
        }
    ]
}