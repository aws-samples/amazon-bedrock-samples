"""
FastAPI application for BDA optimizer web interface.
"""
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
import asyncio
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import sys
import boto3
import uuid
from datetime import datetime
import shlex

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app_sequential_pydantic import main as run_optimizer

# Initialize FastAPI app
app = FastAPI(title="BDA Optimizer UI")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the base directory for the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mount templates and static files with restricted paths
templates_dir = os.path.join(BASE_DIR, "src", "frontend", "templates")
static_dir = os.path.join(BASE_DIR, "src", "frontend", "static")
react_build_dir = os.path.join(BASE_DIR, "src", "frontend", "react", "dist")

# Ensure directories exist and are within the project
if not os.path.exists(templates_dir) or not templates_dir.startswith(BASE_DIR):
    raise ValueError(f"Templates directory not found or outside project: {templates_dir}")

templates = Jinja2Templates(directory=templates_dir)

# Mount static files only if directory exists and is within project
if os.path.exists(static_dir) and static_dir.startswith(BASE_DIR):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount React build (when available) with path validation
if os.path.exists(react_build_dir) and react_build_dir.startswith(BASE_DIR):
    app.mount("/react", StaticFiles(directory=react_build_dir, html=True), name="react")

# Ensure static directory exists within project bounds
os.makedirs(static_dir, exist_ok=True)

# Test endpoint for CORS
@app.get("/api/test")
async def test_cors():
    return {"message": "CORS is working"}



# Pydantic models matching input_0.json structure
class Instruction(BaseModel):
    instruction: str
    data_point_in_document: bool = True
    field_name: str
    expected_output: str
    inference_type: str = "explicit"

class OptimizerConfig(BaseModel):
    project_arn: str
    blueprint_id: str
    document_name: str
    dataAutomation_profilearn: str
    project_stage: str
    input_document: str
    bda_s3_output_location: str
    inputs: List[Instruction]

@app.get("/")
async def home(request: Request):
    """Redirect to React app if available, otherwise serve original UI."""
    if os.path.exists(react_build_dir) and react_build_dir.startswith(BASE_DIR):
        return RedirectResponse(url="/react")
    return await legacy_home(request)

@app.get("/legacy")
async def legacy_home(request: Request):
    """Render the home page with the current configuration."""
    try:
        # Always load input_0.json from project root
        config_path = os.path.join(BASE_DIR, "input_0.json")
        if not config_path.startswith(BASE_DIR):
            raise ValueError("Configuration file path outside project bounds")
            
        with open(config_path, "r") as f:
            config = json.load(f)
        
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "config": config}
        )
    except Exception as e:
        # If input_0.json can't be loaded, return an empty config
        empty_config = {
            "project_arn": "",
            "blueprint_id": "",
            "document_name": "",
            "dataAutomation_profilearn": "",
            "project_stage": "LIVE",
            "input_document": "",
            "bda_s3_output_location": "",
            "inputs": []
        }
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "config": empty_config}
        )

@app.post("/api/update-config")
@app.post("/update-config")
async def update_config(config: OptimizerConfig):
    """Update the input_0.json file with new configuration."""
    try:
        config_path = os.path.join(BASE_DIR, "input_0.json")
        if not config_path.startswith(BASE_DIR):
            raise ValueError("Configuration file path outside project bounds")
            
        with open(config_path, "w") as f:
            json.dump(config.dict(), f, indent=2)
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OptimizerSettings(BaseModel):
    threshold: float = 0.6
    maxIterations: int = 2
    model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    useDoc: bool = True
    clean: bool = True

# Global variable to store the optimizer process
optimizer_process = None

@app.post("/api/clean-logs")
@app.post("/clean-logs")
async def clean_logs():
    """Clean all log files."""
    try:
        import shutil
        
        # Get logs directory with validation
        log_dir = os.path.join(BASE_DIR, "logs")
        if not log_dir.startswith(BASE_DIR):
            raise ValueError("Log directory path outside project bounds")
        
        # Check if directory exists
        if os.path.exists(log_dir):
            # Remove all files in the directory
            for file in os.listdir(log_dir):
                file_path = os.path.join(log_dir, file)
                if os.path.isfile(file_path) and file_path.startswith(log_dir):
                    os.unlink(file_path)
        
        return {"status": "success", "message": "All logs cleaned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-optimizer")
@app.post("/run-optimizer")
async def run_optimization(settings: OptimizerSettings):
    """Run the optimizer with the current configuration and settings."""
    global optimizer_process
    
    try:
        import subprocess
        import time
        import threading
        
        # Clean logs if requested
        if settings.clean:
            # Clean all log files with path validation
            log_dir = os.path.join(BASE_DIR, "logs")
            if not log_dir.startswith(BASE_DIR):
                raise ValueError("Log directory path outside project bounds")
                
            if os.path.exists(log_dir):
                for file in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, file)
                    if os.path.isfile(file_path) and file_path.startswith(log_dir):
                        os.unlink(file_path)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(BASE_DIR, "logs")
        if not log_dir.startswith(BASE_DIR):
            raise ValueError("Log directory path outside project bounds")
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a log file with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_file_path = os.path.join(log_dir, f"optimizer-{timestamp}.log")
        log_file_name = f"optimizer-{timestamp}.log"
        
        # Write initial content to log file
        with open(log_file_path, "w") as log_file:
            log_file.write(f"Optimizer run at {timestamp}\n")
            log_file.write(f"Model: {settings.model}\n")
            log_file.write(f"Threshold: {settings.threshold}\n")
            log_file.write(f"Max iterations: {settings.maxIterations}\n")
            log_file.write(f"Use document strategy: {settings.useDoc}\n")
            log_file.write(f"Clean previous runs: {settings.clean}\n\n")
            log_file.write("Starting optimizer process...\n")
            log_file.flush()
        
        _threshold = shlex.quote(str(settings.threshold))
        # Build command with settings from request
        _useDoc = ""
        if settings.useDoc:
            _useDoc = "--use-doc"
        
        _maxIterations = shlex.quote(str(settings.maxIterations))    
        _clean = ""
        if settings.clean:
            _clean = "--clean"
        
        # Define a function to run the optimizer in a separate thread
        def run_optimizer_process():
            nonlocal log_file_path
            with open(log_file_path, "a") as log_file:
                global optimizer_process
                try:
                    # Execute the command with output redirected to the log file
                    optimizer_process = subprocess.Popen(
                        [
                            "./run_sequential_pydantic.sh",
                            "--threshold", _threshold,
                            "--model", shlex.quote(settings.model),
                            "--max-iterations", _maxIterations,
                            _useDoc,
                            _clean
                        ],
                        stdout=log_file,
                        stderr=log_file,
                        cwd=BASE_DIR  # Use validated base directory
                    )
                    
                    # Write the process ID to the log file for debugging
                    log_file.write(f"\nOptimizer process started with PID: {optimizer_process.pid}\n")
                    log_file.flush()
                    
                    # Wait for process to complete
                    optimizer_process.wait()
                    
                    # Write completion message
                    log_file.write("\nOptimizer process completed.\n")
                    
                    # Ensure all child processes are terminated
                    try:
                        import psutil
                        parent = psutil.Process(optimizer_process.pid)
                        children = parent.children(recursive=True)
                        
                        # Terminate children
                        for child in children:
                            try:
                                child.kill()
                                print(f"Killed child process {child.pid}")
                            except:
                                pass
                        
                        # Also try to kill any related processes using pkill
                        try:
                            # Use the subprocess module that's already imported at the top level
                            result = subprocess.run(["pkill", "-f", "app_sequential_pydantic.py"], check=False)
                            result = subprocess.run(["pkill", "-f", "run_sequential_pydantic.sh"], check=False)
                            print("Killed any remaining optimizer processes using pkill")
                        except Exception as e:
                            print(f"Error killing processes with pkill: {e}")
                    except Exception as e:
                        log_file.write(f"\nError cleaning up processes: {str(e)}\n")
                    
                except Exception as e:
                    # Log any errors
                    log_file.write(f"\nError in optimizer process: {str(e)}\n")
                finally:
                    # Reset the process reference
                    optimizer_process = None
        
        # Start the optimizer in a separate thread
        optimizer_thread = threading.Thread(target=run_optimizer_process)
        optimizer_thread.daemon = True
        optimizer_thread.start()
        
        # Return immediately with the log file path
        # Also include the timestamp for easier matching
        return {
            "status": "running", 
            "message": "Optimization started",
            "log_file": log_file_name,
            "timestamp": timestamp
        }
    except Exception as e:
        # Reset the process reference on error
        optimizer_process = None
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/optimizer-status")
@app.get("/optimizer-status")
async def optimizer_status():
    """Check if the optimizer process is still running."""
    global optimizer_process
    
    try:
        # If optimizer_process is None, it's not running
        if optimizer_process is None:
            return {"status": "not_running"}
        
        # Check if the process is still running
        if optimizer_process.poll() is None:
            # Process is still running
            return {"status": "running"}
        else:
            # Process has completed
            return {"status": "completed", "return_code": optimizer_process.returncode}
    except Exception as e:
        print(f"Error checking optimizer status: {e}")
        # If there's an error, assume it's not running
        return {"status": "not_running", "error": str(e)}

@app.post("/api/stop-optimizer")
@app.post("/stop-optimizer")
async def stop_optimization():
    """Stop the running optimizer process."""
    global optimizer_process
    
    try:
        import signal
        import psutil
        import os
        import subprocess
        
        # Use pkill to kill all processes related to the optimizer
        # This is more robust than trying to find and kill processes individually
        try:
            # Kill all processes with app_sequential_pydantic.py in the command line
            subprocess.run(["pkill", "-f", "app_sequential_pydantic.py"], check=False)
            # Kill all processes with run_sequential_pydantic.sh in the command line
            subprocess.run(["pkill", "-f", "run_sequential_pydantic.sh"], check=False)
            print("Killed optimizer processes using pkill")
        except Exception as e:
            print(f"Error using pkill: {e}")
        
        # Also try the ps approach as a fallback
        try:
            # Find all processes with the name "python" or "python3"
            # This will help us find all related Python processes
            result = subprocess.run(
                ["ps", "-ef"], 
                capture_output=True, 
                text=True
            )
            
            # Look for python processes that might be running the optimizer
            for line in result.stdout.splitlines():
                if "app_sequential_pydantic.py" in line or "run_sequential_pydantic.sh" in line:
                    try:
                        # Extract PID from the ps output
                        parts = line.split()
                        if len(parts) > 1:
                            process_pid = int(parts[1])
                            # Kill the process
                            os.kill(process_pid, signal.SIGKILL)
                            print(f"Killed process {process_pid}")
                    except Exception as e:
                        print(f"Error killing process: {e}")
        except Exception as e:
            print(f"Error using ps approach: {e}")
        
        # If optimizer_process is not None, try to kill it directly
        if optimizer_process:
            try:
                # Get the process and all its children
                parent = psutil.Process(optimizer_process.pid)
                children = parent.children(recursive=True)
                
                # Terminate children first
                for child in children:
                    try:
                        child.kill()  # Use kill instead of terminate for more forceful termination
                    except:
                        pass
                
                # Kill the main process
                optimizer_process.kill()  # Use kill instead of terminate
                
                # Wait for process to actually terminate
                try:
                    optimizer_process.wait(timeout=5)
                except:
                    pass
                
                # If process is still running, use SIGKILL
                if optimizer_process.poll() is None:
                    os.kill(optimizer_process.pid, signal.SIGKILL)
            except Exception as e:
                print(f"Error killing optimizer_process: {e}")
        
        # Reset the process reference
        optimizer_process = None
        
        # Add a message to the current log file if it exists
        log_dir = os.path.join(BASE_DIR, "logs")
        if not log_dir.startswith(BASE_DIR):
            raise ValueError("Log directory path outside project bounds")
            
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if 
                        (f.startswith("optimizer-") or f.startswith("bda_optimizer_")) and 
                        f.endswith(".log")]
            if log_files:
                log_files.sort(reverse=True)  # Most recent first
                latest_log = os.path.join(log_dir, log_files[0])
                if latest_log.startswith(log_dir):  # Additional validation
                    with open(latest_log, "a") as f:
                        f.write("\n\nOptimizer process was manually stopped by user.\n")
        
        return {"status": "success", "message": "Optimizer processes stopped successfully"}
    except Exception as e:
        print(f"Error in stop_optimization: {e}")
        return {"status": "error", "message": f"Error stopping optimizer: {str(e)}"}

@app.get("/api/view-log/{log_file}")
@app.get("/view-log/{log_file}")
async def view_log(log_file: str):
    """View a log file."""
    try:
        # Validate log file name to prevent directory traversal
        if ".." in log_file or "/" in log_file or "\\" in log_file:
            raise HTTPException(status_code=400, detail="Invalid log file name")
            
        log_dir = os.path.join(BASE_DIR, "logs")
        if not log_dir.startswith(BASE_DIR):
            raise ValueError("Log directory path outside project bounds")
            
        log_path = os.path.join(log_dir, log_file)
        
        # Ensure the resolved path is still within the log directory
        if not log_path.startswith(log_dir):
            raise HTTPException(status_code=400, detail="Invalid log file path")
        
        # Print debug information
        print(f"Requested log file: {log_file}")
        print(f"Full log path: {log_path}")
        print(f"Log directory exists: {os.path.exists(log_dir)}")
        print(f"Log file exists: {os.path.exists(log_path)}")
        
        # List available log files
        if os.path.exists(log_dir):
            available_logs = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        else:
            available_logs = []
        print(f"Available log files: {available_logs}")
        
        # If the exact file doesn't exist, try to find a similar one
        if not os.path.exists(log_path) or not os.path.isfile(log_path):
            # Try to find a log file with a similar timestamp
            similar_logs = [f for f in available_logs if f.startswith(log_file[:15])]
            if similar_logs:
                # Use the first similar log file
                log_file = similar_logs[0]
                log_path = os.path.join(log_dir, log_file)
                # Re-validate the new path
                if not log_path.startswith(log_dir):
                    raise HTTPException(status_code=400, detail="Invalid similar log file path")
                print(f"Using similar log file instead: {log_file}")
            else:
                # If no similar log file is found, return a 404 error
                raise HTTPException(status_code=404, detail=f"Log file not found. Available logs: {available_logs}")
        
        # Read the log file
        with open(log_path, "r") as f:
            content = f.read()
        
        return {"content": content}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error in view_log: {str(e)}")
        # Return a more detailed error message
        raise HTTPException(
            status_code=500, 
            detail=f"Error reading log file: {str(e)}. Please check if the file exists and is readable."
        )

class DocumentUploadRequest(BaseModel):
    bucket_name: str
    s3_prefix: Optional[str] = ""

@app.post("/api/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    bucket_name: str = Form(...),
    s3_prefix: str = Form("")
):
    """Upload a document to S3 and return the S3 URI."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Validate file size (max 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 100MB limit")
        
        # Reset file pointer
        await file.seek(0)
        
        # Generate unique filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = os.path.splitext(file.filename)[1]
        s3_key = f"{s3_prefix.rstrip('/')}/{timestamp}_{unique_id}_{file.filename}" if s3_prefix else f"{timestamp}_{unique_id}_{file.filename}"
        
        # Initialize S3 client
        try:
            s3_client = boto3.client('s3')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize S3 client: {str(e)}")
        
        # Check if bucket exists and is accessible
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot access bucket '{bucket_name}': {str(e)}")
        
        # Upload file to S3
        try:
            s3_client.upload_fileobj(
                file.file,
                bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type or 'application/octet-stream',
                    'Metadata': {
                        'original_filename': file.filename,
                        'upload_timestamp': timestamp,
                        'uploaded_by': 'bda-optimizer'
                    }
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload file to S3: {str(e)}")
        
        # Generate S3 URI
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "s3_uri": s3_uri,
            "bucket_name": bucket_name,
            "s3_key": s3_key,
            "file_size": len(file_content),
            "content_type": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/list-s3-buckets")
async def list_s3_buckets():
    """List available S3 buckets for the current AWS account."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.list_buckets()
        
        buckets = []
        for bucket in response['Buckets']:
            try:
                # Try to get bucket location
                location_response = s3_client.get_bucket_location(Bucket=bucket['Name'])
                region = location_response.get('LocationConstraint') or 'us-east-1'
                
                buckets.append({
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat(),
                    'region': region
                })
            except Exception as e:
                # If we can't get bucket details, still include it but with limited info
                buckets.append({
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat(),
                    'region': 'unknown',
                    'error': str(e)
                })
        
        return {
            "status": "success",
            "buckets": buckets
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list S3 buckets: {str(e)}")

@app.post("/api/validate-s3-access")
async def validate_s3_access(request: DocumentUploadRequest):
    """Validate S3 bucket access and permissions."""
    try:
        s3_client = boto3.client('s3')
        
        # Check if bucket exists and is accessible
        try:
            s3_client.head_bucket(Bucket=request.bucket_name)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cannot access bucket '{request.bucket_name}': {str(e)}",
                "has_read_access": False,
                "has_write_access": False
            }
        
        # Test read access
        has_read_access = False
        try:
            s3_client.list_objects_v2(Bucket=request.bucket_name, MaxKeys=1)
            has_read_access = True
        except Exception as e:
            pass
        
        # Test write access by attempting to put a small test object
        has_write_access = False
        test_key = f"{request.s3_prefix.rstrip('/')}/bda-optimizer-test-{uuid.uuid4()}" if request.s3_prefix else f"bda-optimizer-test-{uuid.uuid4()}"
        try:
            s3_client.put_object(
                Bucket=request.bucket_name,
                Key=test_key,
                Body=b"test",
                Metadata={'test': 'true'}
            )
            # Clean up test object
            s3_client.delete_object(Bucket=request.bucket_name, Key=test_key)
            has_write_access = True
        except Exception as e:
            pass
        
        return {
            "status": "success",
            "bucket_name": request.bucket_name,
            "has_read_access": has_read_access,
            "has_write_access": has_write_access,
            "message": "Bucket access validated"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to validate S3 access: {str(e)}",
            "has_read_access": False,
            "has_write_access": False
        }

class BlueprintRequest(BaseModel):
    project_arn: str
    blueprint_id: str
    project_stage: str = "LIVE"

@app.post("/api/test-blueprint")
async def test_blueprint(request: BlueprintRequest):
    """Test endpoint to verify React-FastAPI communication without AWS calls"""
    return {
        "status": "success",
        "blueprint_name": "Test Blueprint",
        "output_path": "/test/path",
        "properties": [
            {
                "field_name": "test_field",
                "instruction": "Test instruction",
                "expected_output": "",
                "inference_type": "explicit"
            }
        ]
    }

@app.post("/api/fetch-blueprint")
@app.post("/fetch-blueprint")
async def fetch_blueprint(request: BlueprintRequest):
    """Fetch a blueprint from AWS BDA and extract its properties."""
    try:
        print(f"Fetching blueprint: {request.blueprint_id} from project: {request.project_arn}")
        
        from src.aws_clients import AWSClients
        import json
        
        # Initialize AWS clients
        print("Initializing AWS clients...")
        aws_clients = AWSClients()
        print("AWS clients initialized successfully")
        
        # Download the blueprint
        print("Downloading blueprint...")
        output_path, blueprint_details = aws_clients.download_blueprint(
            blueprint_id=request.blueprint_id,
            project_arn=request.project_arn,
            project_stage=request.project_stage
        )
        print(f"Blueprint downloaded to: {output_path}")
        
        # Read the schema file
        print("Reading schema file...")
        with open(output_path, 'r') as f:
            schema_content = f.read()
            print(f"Schema content length: {len(schema_content)}")
            
            # Try to parse as JSON
            try:
                schema = json.loads(schema_content)
                print("Schema parsed successfully as JSON")
            except json.JSONDecodeError:
                print("Schema is not valid JSON, treating as string")
                # If it's not JSON, return empty properties
                return {
                    "status": "success",
                    "blueprint_name": blueprint_details.get('blueprintName', 'Unknown'),
                    "output_path": output_path,
                    "properties": []
                }
        
            # Extract properties from the schema
            properties = []
            if isinstance(schema, dict) and 'properties' in schema:
                for field_name, field_data in schema['properties'].items():
                    properties.append({
                        'field_name': field_name,
                        'instruction': field_data.get('instruction', ''),
                        'expected_output': '',  # Empty by default, to be filled in by the user
                        'inference_type': field_data.get('inferenceType', 'explicit')
                    })
                print(f"Extracted {len(properties)} properties")
            else:
                print("No properties found in schema")
        
        # Return the blueprint details and properties
        return {
            "status": "success",
            "blueprint_name": blueprint_details.get('blueprintName', 'Unknown'),
            "output_path": output_path,
            "properties": properties
        }
    except Exception as e:
        print(f"Error fetching blueprint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/final-schema")
@app.get("/final-schema")
async def get_final_schema():
    """Get the final schema generated by the optimizer."""
    try:
        import os
        import glob
        import json
        
        # Get the output/schemas directory with validation
        schemas_dir = os.path.join(BASE_DIR, "output", "schemas")
        if not schemas_dir.startswith(BASE_DIR):
            raise ValueError("Schemas directory path outside project bounds")
        
        # Check if the directory exists
        if not os.path.exists(schemas_dir):
            return {"status": "error", "message": "Schemas directory not found"}
        
        # Look for the most recent run directory
        run_dirs = glob.glob(os.path.join(schemas_dir, "run_*"))
        if not run_dirs:
            return {"status": "error", "message": "No run directories found"}
        
        # Sort by modification time (most recent first)
        run_dirs.sort(key=os.path.getmtime, reverse=True)
        latest_run_dir = run_dirs[0]
        
        # Validate that the run directory is within schemas_dir
        if not latest_run_dir.startswith(schemas_dir):
            return {"status": "error", "message": "Invalid run directory path"}
        
        # Look for schema_final.json in the latest run directory
        final_schema_path = os.path.join(latest_run_dir, "schema_final.json")
        
        if os.path.exists(final_schema_path) and final_schema_path.startswith(schemas_dir):
            # Read the schema file
            with open(final_schema_path, "r") as f:
                schema_content = f.read()
            
            return {"status": "success", "schema": schema_content}
        else:
            # If schema_final.json doesn't exist, look for the highest numbered schema file
            schema_files = glob.glob(os.path.join(latest_run_dir, "schema_*.json"))
            if not schema_files:
                return {"status": "error", "message": "No schema files found"}
            
            # Extract numbers from filenames and find the highest
            schema_numbers = []
            for schema_file in schema_files:
                # Validate schema file path
                if not schema_file.startswith(schemas_dir):
                    continue
                    
                filename = os.path.basename(schema_file)
                if filename.startswith("schema_") and filename.endswith(".json"):
                    try:
                        # Extract the number part (schema_N.json -> N)
                        number_part = filename[7:-5]  # Remove "schema_" and ".json"
                        if number_part.isdigit():
                            schema_numbers.append(int(number_part))
                    except:
                        pass
            
            if schema_numbers:
                highest_schema = max(schema_numbers)
                highest_schema_path = os.path.join(latest_run_dir, f"schema_{highest_schema}.json")
                
                # Validate the highest schema path
                if highest_schema_path.startswith(schemas_dir):
                    # Read the highest numbered schema file
                    with open(highest_schema_path, "r") as f:
                        schema_content = f.read()
                    
                    return {"status": "success", "schema": schema_content}
            
            return {"status": "error", "message": "No valid schema files found"}
    except Exception as e:
        print(f"Error getting final schema: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/list-logs")
@app.get("/list-logs")
async def list_logs():
    """List all available log files."""
    try:
        log_dir = os.path.join(BASE_DIR, "logs")
        if not log_dir.startswith(BASE_DIR):
            raise ValueError("Log directory path outside project bounds")
            
        os.makedirs(log_dir, exist_ok=True)
        
        # Get all log files (both new and old naming patterns)
        log_files = [f for f in os.listdir(log_dir) if 
                    (f.startswith("optimizer-") or f.startswith("bda_optimizer_")) and 
                    f.endswith(".log")]
        log_files.sort(reverse=True)  # Most recent first
        
        return {"log_files": log_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
