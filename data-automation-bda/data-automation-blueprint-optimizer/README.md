# BDA Blueprint Optimizer

An AI-powered tool to optimize Amazon Bedrock Data Automation (BDA) blueprint instructions using advanced language models. The optimizer analyzes your extraction instructions and generates improved, more specific prompts to enhance data extraction accuracy.

## Features

### Modern React UI
- **Professional AWS Cloudscape Design**: Clean, modern interface matching AWS Console styling
- **Real-time Monitoring**: Live log viewing and status updates during optimization
- **Blueprint Integration**: Direct integration with AWS BDA to fetch and optimize existing blueprints
- **Theme Support**: Light/dark mode toggle for better user experience

### AI-Powered Optimization
- **Instruction Enhancement**: Automatically improves extraction instructions using Claude models
- **Context-Aware**: Analyzes document content to generate more specific prompts
- **Iterative Refinement**: Multiple optimization rounds for continuous improvement
- **Performance Tracking**: Monitors extraction accuracy and suggests improvements

### AWS Integration
- **Blueprint Fetching**: Direct integration with AWS Bedrock Data Automation APIs
- **Schema Management**: Automatic schema generation and validation
- **Multi-Region Support**: Configurable AWS region settings

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │  FastAPI        │    │  AI Optimizer   │
│  (Port 3000)    │◄──►│  Backend        │◄──►│  (Claude)       │
│                 │    │  (Port 8000)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  AWS Cloudscape │    │   AWS BDA APIs  │    │  Local Storage  │
│   Components    │    │                 │    │  (Schemas/Logs) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

### AWS Account Setup
- **AWS Account**: Active AWS account with appropriate billing setup
- **AWS CLI**: Version 2.0+ installed and configured
  ```bash
  aws --version
  aws configure
  aws sts get-caller-identity  # Verify configuration
  ```

### AWS Bedrock Access
- **Model Access**: Request access to Claude models in AWS Bedrock
  1. Navigate to AWS Bedrock Console → Model Access
  2. Request access to the following models:
     - `anthropic.claude-3-sonnet-20240229-v1:0` (recommended)
     - `anthropic.claude-3-haiku-20240307-v1:0` (faster, lower cost)
     - `anthropic.claude-3-opus-20240229-v1:0` (highest quality)
  3. Wait for approval (typically 1-2 business days)
  4. Verify access: `aws bedrock list-foundation-models --region us-west-2`

### AWS Bedrock Data Automation (BDA)
- **BDA Access**: Ensure your AWS account has access to Bedrock Data Automation
- **Project Setup**: Create a BDA project with appropriate blueprints
- **IAM Permissions**: Required permissions for BDA operations:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock-data-automation:GetDataAutomationProject",
          "bedrock-data-automation:ListDataAutomationProjects",
          "bedrock-data-automation:GetBlueprint",
          "bedrock-data-automation:ListBlueprints",
          "bedrock-data-automation:CreateBlueprint",
          "bedrock-data-automation:UpdateBlueprint"
        ],
        "Resource": "*"
      }
    ]
  }
  ```

### S3 Storage Requirements
- **S3 Bucket**: Dedicated S3 bucket for document storage and processing
  - Recommended naming: `your-org-bda-optimizer-{region}-{account-id}`
  - Enable versioning for document history
  - Configure appropriate lifecycle policies
- **S3 Permissions**: Required IAM permissions:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        "Resource": [
          "arn:aws:s3:::your-bda-bucket",
          "arn:aws:s3:::your-bda-bucket/*"
        ]
      }
    ]
  }
  ```

### IAM Role Configuration
Create an IAM role or user with the following managed policies:
- `AmazonBedrockFullAccess` (or custom policy with specific model access)
- `AmazonS3FullAccess` (or custom policy for your specific bucket)
- Custom policy for BDA operations (see above)

### Network and Security
- **VPC Configuration**: If running in VPC, ensure:
  - Internet gateway for external API calls
  - NAT gateway for private subnet access
  - Security groups allowing HTTPS (443) outbound
- **Endpoint Access**: Consider VPC endpoints for:
  - S3 (`com.amazonaws.region.s3`)
  - Bedrock (`com.amazonaws.region.bedrock`)
  - Bedrock Runtime (`com.amazonaws.region.bedrock-runtime`)

### Development Environment

- **Python 3.8+**
- **Node.js 16+** and npm
- **AWS CLI** configured with appropriate permissions
- **AWS Bedrock Data Automation** access
- **Environment variables** configured (see Configuration section)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd bda-blueprint-optimizer
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install React Dependencies
```bash
cd src/frontend/react
npm install
cd ../../..
```

### 4. Configure Environment
Create a `.env` file in the root directory:
```bash
# AWS Configuration
AWS_REGION=us-west-2
ACCOUNT=your-aws-account-id
AWS_MAX_RETRIES=3
AWS_CONNECT_TIMEOUT=500
AWS_READ_TIMEOUT=1000

# Model Configuration
DEFAULT_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

## Running the Application

### Option 1: Development Mode (Recommended)
Start both React frontend and FastAPI backend:
```bash
bash run_dev.sh
```

This will start:
- **FastAPI Backend**: http://localhost:8000
- **React Frontend**: http://localhost:3000
- **Legacy UI**: http://localhost:8000/legacy

### Option 2: Manual Start
Start services individually:

**Backend:**
```bash
python -m uvicorn src.frontend.app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd src/frontend/react
npm run dev
```

## Usage Guide

### 1. Configure Your Project
- **Project ARN**: Enter your AWS BDA project ARN
- **Blueprint ID**: Specify the blueprint you want to optimize
- **Output Location**: S3 location for results

### 2. Upload Document (New Feature)
The application now includes a built-in document upload feature:
- **Select S3 Bucket**: Choose from your available S3 buckets
- **Set S3 Prefix**: Optionally specify a folder path (e.g., `documents/input/`)
- **Bucket Validation**: Automatic validation of read/write permissions
- **File Upload**: Drag and drop or select files up to 100MB
- **Supported Formats**: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, TIFF
- **Auto-Configuration**: Uploaded document S3 URI is automatically set in configuration

### 3. Fetch Blueprint
Click "Fetch Blueprint" to download the current blueprint schema from AWS BDA. This populates the instructions table with existing extraction fields.

### 4. Set Expected Outputs
Fill in the "Expected Output" column with sample values for each field. This helps the AI understand what you're trying to extract.

### 5. Configure Optimization Settings
- **Threshold**: Similarity threshold for optimization (0.0-1.0)
- **Max Iterations**: Maximum number of optimization rounds
- **Model**: Claude model to use for optimization
- **Use Document Strategy**: Whether to analyze document content
- **Clean Logs**: Clear previous run logs

### 6. Run Optimization
Click "Run Optimizer" to start the AI optimization process. Monitor progress in real-time through:
- **Status Indicator**: Shows current optimization state
- **Live Logs**: Real-time log output with auto-refresh
- **Progress Tracking**: Iteration progress and performance metrics

### 7. Review Results
Once complete, the "Final Schema" section displays the optimized blueprint with improved instructions.

## Key Features Explained

### Blueprint Fetching
- Connects directly to AWS Bedrock Data Automation APIs
- Downloads existing blueprint schemas
- Auto-populates configuration fields
- Supports multiple project stages (LIVE, DEVELOPMENT)

### AI Optimization Process
1. **Analysis**: AI analyzes your current instructions and expected outputs
2. **Enhancement**: Generates more specific, context-aware prompts
3. **Validation**: Tests improved instructions against sample data
4. **Iteration**: Refines instructions through multiple rounds
5. **Finalization**: Produces optimized schema ready for deployment

### Real-time Monitoring
- **Live Status Updates**: Automatic status polling every 2 seconds
- **Log Streaming**: Real-time log viewing with 1-second refresh
- **Progress Indicators**: Visual feedback on optimization progress
- **Error Handling**: Clear error messages and troubleshooting guidance

## File Structure

```
bda-blueprint-optimizer/
├── src/
│   ├── frontend/
│   │   ├── react/                 # Modern React UI
│   │   │   ├── src/
│   │   │   │   ├── components/    # React components
│   │   │   │   ├── contexts/      # State management
│   │   │   │   └── services/      # API services
│   │   │   └── package.json
│   │   ├── app.py                 # FastAPI backend
│   │   └── templates/             # Legacy UI templates
│   ├── aws_clients.py             # AWS API integration
│   └── ...                        # Core optimization logic
├── output/                        # Generated schemas and results
├── logs/                          # Optimization logs
├── requirements.txt               # Python dependencies
├── run_dev.sh                     # Development startup script
└── README.md
```

## API Endpoints

### Configuration
- `POST /api/update-config` - Update optimization configuration
- `POST /api/fetch-blueprint` - Fetch blueprint from AWS BDA

### Document Upload
- `POST /api/upload-document` - Upload document to S3
- `GET /api/list-s3-buckets` - List available S3 buckets
- `POST /api/validate-s3-access` - Validate S3 bucket access and permissions

### Optimization
- `POST /api/run-optimizer` - Start optimization process
- `GET /api/optimizer-status` - Check optimization status
- `POST /api/stop-optimizer` - Stop running optimization

### Results
- `GET /api/final-schema` - Get optimized schema
- `GET /api/list-logs` - List available log files
- `GET /api/view-log/{log_file}` - View specific log file

## Troubleshooting

### Common Issues

**CORS Errors**
- Ensure FastAPI backend is running on port 8000
- Check that CORS middleware is properly configured

**AWS Authentication**
- Verify AWS CLI is configured: `aws sts get-caller-identity`
- Ensure proper IAM permissions for Bedrock Data Automation
- Check region configuration matches your project ARN

**Blueprint Fetching Fails**
- Verify project ARN and blueprint ID are correct
- Ensure AWS region matches the project region
- Check IAM permissions for `bedrock-data-automation:GetDataAutomationProject`

**Document Upload Issues**
- Verify S3 bucket exists and is accessible
- Check IAM permissions for S3 operations (GetObject, PutObject, ListBucket)
- Ensure file size is under 100MB limit
- Verify supported file formats: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, TIFF

**S3 Access Validation Fails**
- Check bucket permissions and policies
- Verify AWS credentials have S3 access
- Ensure bucket is in the same region as your AWS profile
- Check for bucket-level restrictions or VPC endpoint configurations

**Optimization Hangs**
- Check Claude model availability in your region
- Verify sufficient AWS Bedrock quotas
- Monitor logs for specific error messages

### Log Analysis
- Use "Auto-Refresh" toggle for real-time log monitoring
- Check `logs/` directory for detailed optimization traces
- Review `output/schemas/` for generated schema files

### Security Considerations
- **File Path Validation**: All file operations are restricted to project subdirectories
- **S3 Access Control**: Bucket validation ensures proper read/write permissions
- **Input Sanitization**: File names and paths are validated to prevent directory traversal
- **Size Limits**: File uploads are limited to 100MB to prevent resource exhaustion

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly with both UIs
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review log files for specific error messages
3. Ensure all prerequisites are properly configured
4. Contact the development team for additional support