#!/bin/bash

# Install dependencies
python3 -m pip install -r requirements.txt

# Create necessary directories if they don't exist
mkdir -p src/frontend/templates
mkdir -p src/frontend/static

# Run the FastAPI application
python3 -m uvicorn src.frontend.app:app --host 0.0.0.0 --port 8000 --reload
