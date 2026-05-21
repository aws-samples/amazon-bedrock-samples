from crewai import agents
from pathlib import Path
from crewai.crews.crew_output import CrewOutput
import os 

agent_thoughts = []
task_outputs = {}

AGENT_RPM = 4 # max requests per minute the agent can make

def cache_func(args, result):
    print("cache result", result)
    return True

def _step_callback(*args, **kwargs):
    """
    A method that can accept any number of positional and keyword arguments.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    # Process positional arguments
    for i, arg in enumerate(args):
        print(f"Positional argument {i}: {arg}")
        if type(arg) == agents.parser.AgentAction:

            print(arg.thought)
            print(arg.tool)
            print(arg.tool_input)
            print(arg.text)
            print(arg.result)
            agent_thoughts.append(
                {
                    "thought": arg.thought,
                    "tool": arg.tool,
                    "tool_input": arg.tool_input,
                    "text": arg.text,
                    "result": arg.result
                }
            )

    # Process keyword arguments
    for key, value in kwargs.items():
        print(f"Keyword argument {key}: {value}")

def _task_callback(task_output) -> None:
    """
    Callback function to process task outputs with support for different output formats.
    
    Args:
        task_output: TaskOutput object containing the task results
        
    The TaskOutput object has the following attributes:
    - description: Task description
    - summary: Auto-generated summary from first 10 words of description
    - raw: Raw string output
    - pydantic: Pydantic model output (if configured) 
    - json_dict: Dictionary output (if JSON configured)
    - agent: Agent that executed the task
    - output_format: Format of the output (RAW, JSON, or PYDANTIC)
    """
    try:
        # Print basic task info
        print(f"\nTask Output Summary:")
        print(f"Description: {task_output.description}")
        print(f"Agent: {task_output.agent}")
        print(f"Task Name: {task_output.name}")
        
        # Handle different output formats
        if hasattr(task_output, 'pydantic') and task_output.pydantic:
            print("\nPydantic Output:")
            print(task_output.pydantic.model_dump())
            task_outputs[task_output.name] = task_output.pydantic.model_dump()
            
        elif hasattr(task_output, 'json_dict') and task_output.json_dict:
            print("\nJSON Output:")
            print(task_output.json_dict)
            
        else:
            print("\nRaw Output:")
            print(task_output.raw)

        # Convert to dictionary for additional processing if needed
        output_dict = task_output.to_dict() if hasattr(task_output, 'to_dict') else {}
        print(output_dict)
        # Store output in the cache
        # cache_func(task_output, output_dict)
        
    except Exception as e:
        print(f"Error processing task output: {str(e)}")

def task_summary(crew_output: CrewOutput):
    """
    Prints a summary of the task outputs executed by the crew.

    Args:
        tasks: List of tasks executed by the crew
    """
    combined_summary = ""
    for task in crew_output.tasks_output:
        # print("task name", task.name)
        # print("task description", task.description)
        # print("task expected output", task.raw)
        combined_summary += "\n\n" + task.raw.replace('```','')

    return combined_summary



def ensure_dir_path(dir_path: str) -> str:
    """
    Creates necessary directories for the memory database if they don't exist
    and returns the full database path.

    Args:
        dir_path (str): directory path

    Returns: dir_path
    """

    # Create directories if they don't exist
    try:
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    except (PermissionError, OSError) as e:
        # Fallback: Use user's home directory
        print(f"Warning: Could not write to {dir_path}: {e}")
        home_dir = str(Path.home())
        memory_dir = os.path.join(home_dir,dir_path)
        print(f"Falling back to: {memory_dir}")
        os.makedirs(memory_dir, exist_ok=True)
        return home_dir