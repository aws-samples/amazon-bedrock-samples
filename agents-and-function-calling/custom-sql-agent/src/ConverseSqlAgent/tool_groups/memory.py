
def read_memory(self, memory_id):
    """
    Retrieves the memory from the specified memory_id
    
    Parameters:
    - memory_id (int) The memory_id to retrieve from DynamoDB
    
    Returns:
    - (string) The content of the record 
    
    """
        
    try:
        response = self.table.get_item(Key={'id': memory_id})
        if 'Item' in response:
            memory = response['Item'].get('memory', '')
        else:
            memory = ''
        
        final_output = f"Contents of memory id {memory_id}: {memory}"
    except Exception as e:
        final_output = f"Encountered error: {e}"
        
    # print(final_output)
    return final_output
    
## ReadMemory ToolSpec
READ_MEMORY_TOOLSPEC={
    "toolSpec": {
        "name": "read_memory",
        "description": "Use this tool to read the memory contents given a memory id",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "This is the memory Id to retrieve"
                    }
                }
            }
        }
    }
}
    
    
def write_memory(self, memory_id, contents):
    """
    Overrides the contents of the record in memory_id
    
    Parameters:
    - memory_id (int) The memory_id to write to in DynamoDB
    - memory (string) The content to set
    
    Returns:
    -  final_output (string) Confirmation of execution
    
    """
        
    try:
        self.table.put_item(
            Item={
                'id': memory_id,
                'memory': contents
            }
        )
        final_output = f"Successfully saved memory id {memory_id}"
        
    except Exception as e:
        final_output = f"Encountered error: {e}"
        
    return final_output

# WriteMemory ToolSpec
WRITE_MEMORY_TOOLSPEC={
    "toolSpec": {
        "name": "write_memory",
        "description": "Completely override the memory with the contents given a memory_id.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "This is the memory Id to retrieve"
                    },
                    "contents": {
                        "type": "string",
                        "description": "This is the new memory contents to write"
                    }
                }
            }
        }
    }
}

def append_memory(self, memory_id, contents):
    """
    Appends to the memory in the database
    
    Parameters:
    - memory_id (int) The memory_id to append to in DynamoDB
    - contents (string) The content to append
    
    Returns:
    - final_output (string) Confirmation of execution 
    
    """
    
    try:
        response = self.table.get_item(Key={'id': memory_id})
        if 'Item' in response:
            memory = response['Item'].get('memory', '')
        else:
            memory = ''
            
        memory = memory + "\n" + contents

        self.table.put_item(
            Item={
                'id': memory_id,
                'memory': memory
            }
        )
        final_output = f"Successfully appended to memory id {memory_id}"
        
    except Exception as e:
        final_output = f"Encountered error: {e}"
        
    # print(final_output)
    return final_output

## AppendMemory ToolSpec
APPEND_MEMORY_TOOLSPEC={
    "toolSpec": {
        "name": "append_memory",
        "description": "Use this tool to append to the memory stored at the memory_id.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "This is the memory Id to retrieve"
                    },
                    "contents": {
                        "type": "string",
                        "description": "This is the new memory contents to append"
                    }
                }
            }
        }
    }
}

def delete_memory(self, memory_id):
    """
    Deletes a memory
    
    Parameters:
    - memory_id (int) The memory_id to delete in DynamoDB
    
    Returns:
    - final_output (string) Confirmation
    """
    
    try:
        self.table.delete_item(
            Key={
                "id": memory_id
            }
        )
        final_output = f"Successfully deleted memory_id {memory_id}"
    except Exception as e:
        final_output = f"Encountered error: {e}"
        
    return final_output

DELETE_MEMORY_TOOLSPEC={
    "toolSpec": {
        "name": "delete_memory",
        "description": "Use this tool to delete a memory",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "This is the memory Id to delete"
                    }
                }
            }
        }
    }
}


MEMORY_TOOL_GROUP = {
    "tool_group_name": "MEMORY_TOOL_GROUP",
    "usage_instructions": """
    When using the write_memory tool, it will completely
    override the memory. It will completely delete the contents
    and replace it. Do not append before having at least read the memory.
    """,
    "tools": [
        {
            "tool_spec": WRITE_MEMORY_TOOLSPEC,
            "function": write_memory
        },
        {
            "tool_spec": READ_MEMORY_TOOLSPEC,
            "function": read_memory
        },
        {
            "tool_spec": APPEND_MEMORY_TOOLSPEC,
            "function": append_memory
        },
        {
            "tool_spec": DELETE_MEMORY_TOOLSPEC,
            "function": delete_memory
        }
    ]    
}


