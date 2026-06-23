#!/bin/bash

# Build React app for production

echo "Building React frontend for production..."

cd "$(dirname "$0")/src/frontend/react"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing React dependencies..."
    npm install
fi

# Build the React app
echo "Building React app..."
npm run build

echo "React build completed. Files are in src/frontend/react/dist/"
echo "Start the FastAPI server to serve the React app at http://localhost:8000"