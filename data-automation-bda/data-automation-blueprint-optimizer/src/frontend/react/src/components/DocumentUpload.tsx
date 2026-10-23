import React, { useState, useRef } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  FormField,
  Input,
  Select,
  Alert,
  ProgressBar,
  Box,
  TextContent,
  ColumnLayout
} from '@cloudscape-design/components';

interface DocumentUploadProps {
  onUploadSuccess: (s3Uri: string) => void;
  currentS3Uri?: string;
}

interface S3Bucket {
  name: string;
  region: string;
  creation_date: string;
}

interface UploadProgress {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadSuccess, currentS3Uri }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [buckets, setBuckets] = useState<S3Bucket[]>([]);
  const [selectedBucket, setSelectedBucket] = useState<string>('');
  const [s3Prefix, setS3Prefix] = useState<string>('bda-optimizer/documents');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    status: 'idle',
    progress: 0,
    message: ''
  });
  const [bucketValidation, setBucketValidation] = useState<{
    status: 'idle' | 'validating' | 'valid' | 'invalid';
    message: string;
    hasReadAccess: boolean;
    hasWriteAccess: boolean;
  }>({
    status: 'idle',
    message: '',
    hasReadAccess: false,
    hasWriteAccess: false
  });
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load S3 buckets on component mount
  React.useEffect(() => {
    loadS3Buckets();
  }, []);

  // Validate bucket access when bucket is selected
  React.useEffect(() => {
    if (selectedBucket) {
      validateBucketAccess();
    }
  }, [selectedBucket]);

  const loadS3Buckets = async () => {
    try {
      const response = await fetch('/api/list-s3-buckets');
      const data = await response.json();
      
      if (data.status === 'success') {
        setBuckets(data.buckets);
      } else {
        setUploadProgress({
          status: 'error',
          progress: 0,
          message: 'Failed to load S3 buckets. Please check your AWS credentials.'
        });
      }
    } catch (error) {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: 'Failed to connect to backend service.'
      });
    }
  };

  const validateBucketAccess = async () => {
    if (!selectedBucket) return;

    setBucketValidation({ status: 'validating', message: 'Validating bucket access...', hasReadAccess: false, hasWriteAccess: false });

    try {
      const response = await fetch('/api/validate-s3-access', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          bucket_name: selectedBucket,
          s3_prefix: s3Prefix
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        setBucketValidation({
          status: data.has_write_access ? 'valid' : 'invalid',
          message: data.has_write_access 
            ? 'Bucket access validated successfully' 
            : 'Bucket is accessible but lacks write permissions',
          hasReadAccess: data.has_read_access,
          hasWriteAccess: data.has_write_access
        });
      } else {
        setBucketValidation({
          status: 'invalid',
          message: data.message,
          hasReadAccess: false,
          hasWriteAccess: false
        });
      }
    } catch (error) {
      setBucketValidation({
        status: 'invalid',
        message: 'Failed to validate bucket access',
        hasReadAccess: false,
        hasWriteAccess: false
      });
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (100MB limit)
      const maxSize = 100 * 1024 * 1024;
      if (file.size > maxSize) {
        setUploadProgress({
          status: 'error',
          progress: 0,
          message: 'File size exceeds 100MB limit. Please select a smaller file.'
        });
        return;
      }

      setSelectedFile(file);
      setUploadProgress({
        status: 'idle',
        progress: 0,
        message: ''
      });
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedBucket) {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: 'Please select a file and S3 bucket.'
      });
      return;
    }

    if (bucketValidation.status !== 'valid') {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: 'Please select a valid S3 bucket with write permissions.'
      });
      return;
    }

    setUploadProgress({
      status: 'uploading',
      progress: 0,
      message: 'Uploading document...'
    });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('bucket_name', selectedBucket);
      formData.append('s3_prefix', s3Prefix);

      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }));
      }, 200);

      const response = await fetch('/api/upload-document', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);

      const data = await response.json();

      if (data.status === 'success') {
        setUploadProgress({
          status: 'success',
          progress: 100,
          message: `Document uploaded successfully to ${data.s3_uri}`
        });
        
        // Call the success callback
        onUploadSuccess(data.s3_uri);
        
        // Reset form
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        setUploadProgress({
          status: 'error',
          progress: 0,
          message: data.detail || 'Upload failed'
        });
      }
    } catch (error) {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: 'Upload failed. Please try again.'
      });
    }
  };

  const bucketOptions = buckets.map(bucket => ({
    label: `${bucket.name} (${bucket.region})`,
    value: bucket.name
  }));

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Upload a document to S3 for processing with BDA Blueprint Optimizer"
        >
          Document Upload
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        {currentS3Uri && (
          <Alert type="info">
            Current document: <code>{currentS3Uri}</code>
          </Alert>
        )}

        <ColumnLayout columns={2}>
          <FormField
            label="S3 Bucket"
            description="Select the S3 bucket where the document will be uploaded"
          >
            <Select
              selectedOption={selectedBucket ? { label: selectedBucket, value: selectedBucket } : null}
              onChange={({ detail }) => setSelectedBucket(detail.selectedOption.value || '')}
              options={bucketOptions}
              placeholder="Select an S3 bucket"
              loadingText="Loading buckets..."
              empty="No buckets available"
            />
          </FormField>

          <FormField
            label="S3 Prefix (Optional)"
            description="Folder path within the bucket (e.g., documents/input/)"
          >
            <Input
              value={s3Prefix}
              onChange={({ detail }) => setS3Prefix(detail.value)}
              placeholder="bda-optimizer/documents"
            />
          </FormField>
        </ColumnLayout>

        {bucketValidation.status !== 'idle' && (
          <Alert
            type={bucketValidation.status === 'valid' ? 'success' : 
                  bucketValidation.status === 'validating' ? 'info' : 'error'}
          >
            <TextContent>
              <p>{bucketValidation.message}</p>
              {bucketValidation.status === 'valid' && (
                <Box>
                  <p>✓ Read Access: {bucketValidation.hasReadAccess ? 'Yes' : 'No'}</p>
                  <p>✓ Write Access: {bucketValidation.hasWriteAccess ? 'Yes' : 'No'}</p>
                </Box>
              )}
            </TextContent>
          </Alert>
        )}

        <FormField
          label="Select Document"
          description="Choose a document file to upload (max 100MB)"
        >
          <SpaceBetween direction="vertical" size="s">
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileSelect}
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.tiff,.tif"
              style={{
                padding: '8px',
                border: '2px dashed #ccc',
                borderRadius: '4px',
                width: '100%',
                cursor: 'pointer'
              }}
            />
            {selectedFile && (
              <Box>
                <TextContent>
                  <p><strong>Selected file:</strong> {selectedFile.name}</p>
                  <p><strong>Size:</strong> {formatFileSize(selectedFile.size)}</p>
                  <p><strong>Type:</strong> {selectedFile.type || 'Unknown'}</p>
                </TextContent>
              </Box>
            )}
          </SpaceBetween>
        </FormField>

        {uploadProgress.status === 'uploading' && (
          <ProgressBar
            value={uploadProgress.progress}
            label="Upload Progress"
            description={uploadProgress.message}
          />
        )}

        {uploadProgress.message && uploadProgress.status !== 'uploading' && (
          <Alert
            type={uploadProgress.status === 'success' ? 'success' : 'error'}
          >
            {uploadProgress.message}
          </Alert>
        )}

        <Box textAlign="right">
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={
              !selectedFile || 
              !selectedBucket || 
              uploadProgress.status === 'uploading' ||
              bucketValidation.status !== 'valid'
            }
            loading={uploadProgress.status === 'uploading'}
          >
            Upload Document
          </Button>
        </Box>
      </SpaceBetween>
    </Container>
  );
};

export default DocumentUpload;
