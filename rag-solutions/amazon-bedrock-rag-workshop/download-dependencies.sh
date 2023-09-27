#!/bin/sh
cd "$(dirname "${BASH_SOURCE[0]}")"

DEPENDENCY_DIR="./dependencies/"

if [ -d "$DEPENDENCY_DIR" ]
then
    echo "Existing dependency directory found, removing and replacing..."
    rm -r "$DEPENDENCY_DIR"  
fi

echo "Creating dependency directory"
mkdir -p "$DEPENDENCY_DIR" && \
cd "$DEPENDENCY_DIR" && \

echo "Downloading dependencies"
curl -sS https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip > sdk.zip && \

echo "Unpacking dependencies"
# (SageMaker Studio system terminals don't have `unzip` utility installed)
if command -v unzip &> /dev/null
then
    unzip -o sdk.zip && rm sdk.zip && echo "Done"
else
    echo "'unzip' command not found: Trying to unzip via Python"
    python -m zipfile -e sdk.zip . && rm sdk.zip && echo "Done"
fi