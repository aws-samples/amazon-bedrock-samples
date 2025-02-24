## Dataset Validation for Fine-tuning Open Source Models
Before you create a fine-tuning job in the Amazon Bedrock console, utilize the provided script to validate your dataset first, which would allow you to identify formatting errors (if any) faster and save costs.

### Usage

Install the latest version of python [here](https://www.python.org/downloads/) if you haven't already.

Download the `dataset_validation` folder, `cd` into the root directory, and run the dataset validation script:

```
python3 dataset_validation.py -d <dataset type> -f <file path> -m <model name>
```

1. Dataset type options
    - train
    - validation

2. Model name options
    - meta.llama3-1-8b-instruct-v1
    - meta.llama3-1-70b-instruct-v1
    - meta.llama3-2-1b-instruct-v1
    - meta.llama3-2-3b-instruct-v1
    - meta.llama3-2-11b-instruct-v1
    - meta.llama3-2-90b-instruct-v1


### Features
1. Validates the `JSONL` format
2. Checks that the `train` dataset has <= 10k rows and `validation` dataset has <= 1k rows
    - Each conversation should only take up 1 row
3. For each row
    - For models that use the prompt completion format, the script checks that
        - required keys exists
        - invalid types are not present
    - For models that use the messaging format, the script checks that
        - system array (if it exists) only contains 1 element
        - required keys exists
        - invalid types are not present
        - given `role` for each message is supported
        - messages with the `assistant` role do not contain an image

### Limitations Not Validated by the Script
1. Images
    - Size <= 10 MB
    - Format must be one of `png`, `jpeg`, `gif`, `webp`
    - Dimensions <= 8192 x 8192 pixels
2. Input token length of each dataset row <= 16K