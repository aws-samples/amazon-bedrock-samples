#!/bin/bash

# Development script to run both FastAPI backend and React frontend
# with security restrictions and path validation

echo "Starting BDA Optimizer Development Environment..."

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Validate we're in the correct project directory
if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]] || [[ ! -d "$PROJECT_ROOT/src/frontend" ]]; then
    echo "Error: Script must be run from the project root directory"
    echo "Expected files/directories not found in: $PROJECT_ROOT"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo "Shutting down development servers..."
    if [[ -n "$FASTAPI_PID" ]]; then
        kill $FASTAPI_PID 2>/dev/null
        echo "FastAPI server stopped"
    fi
    if [[ -n "$REACT_PID" ]]; then
        kill $REACT_PID 2>/dev/null
        echo "React server stopped"
    fi
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Validate Python environment
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

# Check if required Python packages are installed
echo "Checking Python dependencies..."
if ! python -c "import fastapi, uvicorn, boto3" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Start FastAPI backend with restricted working directory
echo "Starting FastAPI backend on port 8000..."
cd "$PROJECT_ROOT"
python -m uvicorn src.frontend.app:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 3

# Validate React environment
REACT_DIR="$PROJECT_ROOT/src/frontend/react"
if [[ ! -d "$REACT_DIR" ]]; then
    echo "Error: React directory not found at $REACT_DIR"
    exit 1
fi

# Start React frontend
echo "Starting React frontend on port 3000..."
cd "$REACT_DIR"

# Validate Node.js environment
if ! command -v npm &> /dev/null; then
    echo "Error: Node.js/npm is not installed or not in PATH"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [[ ! -d "node_modules" ]]; then
    echo "Installing React dependencies..."
    npm install
fi

# Check if package.json exists
if [[ ! -f "package.json" ]]; then
    echo "Error: package.json not found in React directory"
    exit 1
fi

npm run dev &
REACT_PID=$!

echo ""
echo "Development servers started successfully:"
echo "- FastAPI Backend: http://localhost:8000"
echo "- React Frontend: http://localhost:3000"
echo "- Legacy UI: http://localhost:8000/legacy"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Security: File operations restricted to project subdirectories"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for background processes
wait