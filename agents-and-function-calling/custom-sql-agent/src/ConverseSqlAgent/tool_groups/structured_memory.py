import json

from prompts import STRUCTURED_MEMORY_TOOL_GROUP_INSTRUCTIONS_PROMPT

def create_memory_index(self):
    """
    Creates a new memory index    
    """
    
    memory_index = {
        "memories": [
            {
                "memory_id": "1",
                "is_delete_protected": True,
                "is_write_protected": False,
                "title": "Main memory index",
                "description": "This is the main memory index containing mapings to the memories."
            },
            {
                "memory_id": "2",
                "is_delete_protected": True,
                "is_write_protected": False,
                "title": "Best Practices and Error Avoidance",
                "description": "Use this memory to store any lessons learned"
            }
        ]   
    }
    
    self.table.put_item(
        Item={
            "id": "1",
            "contents": json.dumps(memory_index)
        }
    )
    
    return memory_index


def get_memory_index(self):
    """
    Retrieves the memory index
    """
    
    response = self.table.get_item(
        Key={
            "id": "1"
        }
    )
    
    if "Item" in response:
        contents = response["Item"].get("contents", None)
        
        if contents:
            memory = json.loads(contents)
        else:
            memory = None
        
    else:
        memory = None
        
    return memory

def update_memory_index_entry(self, memory_id, title, description, 
                              is_delete_protected=False, is_write_protected=False):
    
    # Index entry
    index_entry = {
        "memory_id": memory_id,
        "is_delete_protected": is_delete_protected,
        "is_write_protected": is_write_protected,
        "title": title,
        "description": description
    }
    
    # Retrieve the memory index first
    memory = self.get_memory_index()
    
    if memory:
    
        existing_memory_found = False
        
        # Updates an existing entry
        for i in range(len(memory["memories"])):
            if memory["memories"][i]["memory_id"] == index_entry["memory_id"]:
                memory["memories"][i] = index_entry
                existing_memory_found = True
                break
        
        # Appends if new
        if not existing_memory_found:
            memory["memories"].append(index_entry)
        
        self.table.put_item(
            Item={
                "id": "1",
                "contents": json.dumps(memory)
            }
        )
        
        return {
            "statusCode": 200,
            "body": memory
        }
    
    else:
        return {
            "statusCode": 400,
            "body": "Main memory index is empty. You must initialize it first."
        }
    

def delete_memory_index_entry(self, memory_id):
    
    memory = self.get_memory_index()
    
    for i in range(len(memory["memories"])):
        if memory["memories"][i]["memory_id"] == str(memory_id):
            
            if memory["memories"][i]["is_delete_protected"] == "True":
                return {
                    "statusCode": 401,
                    "body": f"Memory id {memory_id} cannot be deleted as it is marked as delete protected."
                }
                
            # Delete from dynamo db    
            self.table.delete_item(
                Key={
                    "id": memory_id
                }
            )
            
            # Delete from index
            memory["memories"].pop(i)
            break
    
    self.table.put_item(
        Item={
            "id": "1",
            "contents": json.dumps(memory)
        }
    )

    return {
        "statusCode": 200,
        "body": memory
    }

def write_memory(self, memory_id, title, description, contents, is_delete_protected=False, is_write_protected=False):
    """Updates the memory index first then write the contents"""
    
    # Block direct updates to the main memory index
    if memory_id == "1":
        return {
            "statusCode": 401,
            "body": "You cannot use write_memory to update the main memory index."
        }
    
    # Check if memory exists
    memory_index = self.get_memory_index()
    
    if memory_index:
    
        for i in range(len(memory_index["memories"])):
            if memory_index["memories"][i]["memory_id"] == str(memory_id):
                
                # Check if is_write_protected
                
                if str(memory_index["memories"][i]["is_write_protected"]) == "True":
                    return {
                        "statusCode": 401,
                        "body": f"Memory id {memory_id} is write protected. You cannot update this memory."
                    }

        # Update the index
        self.update_memory_index_entry(memory_id, title, description, is_delete_protected, is_write_protected)

        # Memory contents
        memory_contents = {
            "title": title,
            "is_delete_protected": str(is_delete_protected),
            "is_write_protected": str(is_write_protected),
            "description": description,
            "contents": contents
        }

        # Write the memory
        self.table.put_item(
            Item={
                "id": memory_id,
                "contents": json.dumps(memory_contents)
            }
        )

        return {
            "statusCode": 200,
            "body": f"Successfully saved memory_id {memory_id}."
        }
        
    else:
        return {
            "statusCode": 400,
            "body": "Main memory index is empty. You must initialize it first."
        }
    
def read_memory(self, memory_id):
    """Returns the contents of a memory"""
    
    response = self.table.get_item(
        Key={
            "id": memory_id
        }
    )
    
    if "Item" in response:
        contents = json.loads(response["Item"].get("contents"))
        
        return {
            "statusCode": 200,
            "body": contents
        }
    
    else:
        return {
            "statusCode": 404,
            "body": "Memory not found or is empty"
        }
    

## ReadMemory ToolSpec
CREATE_MEMORY_INDEX_TOOLSPEC={
    "toolSpec": {
        "name": "create_memory_index",
        "description": """Use this tool to initialize the main memory if it's empty. There are no paramaters to this tool.""",
        "inputSchema": {
            "json": {
                "type": "object"
            }
        }
    }
}

GET_MEMORY_INDEX_TOOLSPEC={
    "toolSpec": {
        "name": "get_memory_index",
        "description": "Use this tool to retrieve all memories available in the memory index. There are no parameters to this tool.",
        "inputSchema": {
            "json" : {
                "type": "object"
            }
        }
    }
}
    
UPDATE_MEMORY_INDEX_ENTRY_TOOLSPEC = {
    "toolSpec": {
        "name": "update_memory_index_entry",
        "description": "Use this tool to update an existing entry in the memory index.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The unique identifier of the memory to be updated."
                    },
                    "title": {
                        "type": "string",
                        "description": "The new title for the memory entry."
                    },
                    "description": {
                        "type": "string",
                        "description": "The new description for the memory entry."
                    },
                    "is_delete_protected": {
                        "type": "string",
                        "description": """Set to true or false. If set to true, you cannot delete this memory in the future.
                        Only use this if you absolutely sure that it must never be deleted in the future.
                        """
                    },
                    "is_write_protected": {
                        "type": "string",
                        "description": """Set to true or false. If set to false, you cannot modify the contents of this
                        memory in the future. Only use this if you absolutely sure that it shouldn't be modified in the future."""
                    }
                },
                "required": ["memory_id", "title", "description"]
            }                
        }
    }
}

DELETE_MEMORY_INDEX_ENTRY_TOOLSPEC = {
    "toolSpec": {
        "name": "delete_memory_index_entry",
        "description": "Use this tool to delete an entry from the memory index.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The unique identifier of the memory to be deleted."
                    }
                },
                "required": ["memory_id"]
            }
        }

    }
}

WRITE_MEMORY_TOOLSPEC = {
    "toolSpec": {
        "name": "write_memory",
        "description": "Creates or updates an existing memory with the title, description, and contents",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The unique identifier of the memory"
                    },
                    "title": {
                        "type": "string",
                        "description": "A short title of the memory"
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description (max 50 words) summarizing the memory"
                    },
                    "contents": {
                        "type": "string",
                        "description": "The plaintext contents of the memory to write."
                    },
                    "is_delete_protected": {
                        "type": "string",
                        "description": """Set to true or false. If set to true, you cannot delete this memory in the future.
                        Only use this if you absolutely sure that it must never be deleted in the future.
                        """
                    },
                    "is_write_protected": {
                        "type": "string",
                        "description": """Set to true or false. If set to false, you cannot modify the contents of this
                        memory in the future. Only use this if you absolutely sure that it shouldn't be modified in the future."""
                    }
                },
                "required": ["memory_id", "title", "description", "contents"]
            }
        }
    }
}

READ_MEMORY_TOOLSPEC = {
    "toolSpec": {
        "name": "read_memory",
        "description": "Reads the contents of the memory given a memory_id",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The memory_id of the memory to get the contents of"
                    }
                },
                "required": ["memory_id"]
            }
        }
    }
}




    
STRUCTURED_MEMORY_TOOL_GROUP={
    "tool_group_name": "STRUCTURED_MEMORY_TOOL_GROUP",
    "usage_instructions": STRUCTURED_MEMORY_TOOL_GROUP_INSTRUCTIONS_PROMPT,
    "tools": [
        {
            "tool_spec": CREATE_MEMORY_INDEX_TOOLSPEC,
            "function": create_memory_index
        },
        {
            "tool_spec": GET_MEMORY_INDEX_TOOLSPEC,
            "function": get_memory_index
        },
        {
            "tool_spec": UPDATE_MEMORY_INDEX_ENTRY_TOOLSPEC,
            "function": update_memory_index_entry
        },
        {
            "tool_spec": DELETE_MEMORY_INDEX_ENTRY_TOOLSPEC,
            "function": delete_memory_index_entry
        },
        {
            "tool_spec": WRITE_MEMORY_TOOLSPEC,
            "function": write_memory
        },
        {
            "tool_spec": READ_MEMORY_TOOLSPEC,
            "function": read_memory
        }
    ]
}