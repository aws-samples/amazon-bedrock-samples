## Dataset Validation for Model Distillation
Before you create a model distillation job in the Amazon Bedrock console, utilize the provided script to validate your dataset first. This would allow you to identify formatting errors (if any) faster and save costs. More details about the accepted format can be found here: https://docs.aws.amazon.com/bedrock/latest/userguide/prequisites-model-distillation.html

### Usage

Install the last version of python [here](https://www.python.org/downloads/) if you haven't already.

Download the `dataset-validation` folder, `cd` into the root directory, and run the dataset validation script:

```
pip install -r requirements.txt -U
python3 dataset_validator.py -p <path>

# Specifying an output file for detailed validation logs
python3 dataset_validator.py -p <path> -o <log file>

# Specifying the given path is for invocation logs
python3 dataset_validator.py -p <path> -i
```

- Path options
    - file: /path/to/file.jsonl
    - folder: /path/to/folder
    - S3: s3://bucket/key

### Features
1. Validates prompts in the given path satisfy the `bedrock-conversation-2024` format
2. If an output file is given, validation errors for each prompt would be logged in the output file
3. If the invocation logs flag is present, the validator will validate for the invocation logs use-case instead

### Limitations

This script currently does not support the following features:
- Invocation logs validation with filters
- Validating prompts do not contain invalid tags
