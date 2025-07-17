# Amazon Bedrock Data Automation Sample Code

This directory contains sample code for working with Amazon Bedrock Data Automation (BDA).

## Samples

### Video Blueprint with Open Set Object Detection (OSOD)

The `video-blueprint-with-osod.ipynb` notebook demonstrates how to use Amazon Bedrock Data Automation for advanced object detection in videos. It includes:

- Setting up a custom blueprint for object detection with business-friendly field names
- Processing video content with BDA
- Visualizing detected objects with bounding boxes
- Analyzing object detection results across video chapters
- Extracting business insights from video content

The notebook uses the `bda_object_detection_utils.py` utility file, which provides helper functions for:
- Video processing and S3 operations
- Enhanced visualization of object detection results
- Chapter-based object analysis
- Frame extraction with bounding boxes

## Prerequisites

- An AWS account with access to Amazon Bedrock
- Python 3.7+
- Required Python packages: boto3, matplotlib, moviepy, pandas, seaborn, wordcloud

## Getting Started

1. Set up your AWS credentials
2. Install the required Python packages
3. Open the notebook in SageMaker Studio or Jupyter
4. Follow the step-by-step instructions in the notebook

## License

This library is licensed under the MIT-0 License. See the LICENSE file.