"""
Send Notification Lambda Function

This Lambda function sends pipeline completion notifications via SNS.
It includes:
- Presigned URLs for all output files
- Pipeline execution summary
- Stage-level details
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils import split_s3_uri, get_logger

logger = get_logger()
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')


def generate_presigned_urls(
    s3_paths: List[str],
    expiry_days: int = 7
) -> List[Dict[str, str]]:
    """Generate presigned URLs for S3 paths.
    
    Args:
        s3_paths: List of S3 URIs
        expiry_days: Number of days until URLs expire
        
    Returns:
        List of dicts with path, url, and expiration info
    """
    urls = []
    expiry_seconds = expiry_days * 24 * 3600
    
    for s3_path in s3_paths:
        try:
            bucket, key = split_s3_uri(s3_path)
            
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiry_seconds
            )
            
            expires_at = datetime.now() + timedelta(days=expiry_days)
            
            urls.append({
                'path': s3_path,
                'url': presigned_url,
                'expires': expires_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generating presigned URL for {s3_path}: {str(e)}")
            urls.append({
                'path': s3_path,
                'url': None,
                'error': str(e)
            })
    
    return urls


def format_notification_message(
    pipeline_name: str,
    stage_results: List[Dict[str, Any]],
    presigned_urls: List[Dict[str, str]],
    validation: Dict[str, Any],
    is_success: bool = True,
    error_message: str = None
) -> tuple[str, str]:
    """Format notification subject and message.
    
    Args:
        pipeline_name: Name of the pipeline
        stage_results: Results from each stage
        presigned_urls: Presigned URLs for outputs
        validation: Validation results
        is_success: Whether pipeline succeeded
        error_message: Error message if failed
        
    Returns:
        Tuple of (subject, message)
    """
    if is_success:
        subject = f"✅ Pipeline Complete: {pipeline_name}"
    else:
        subject = f"❌ Pipeline Failed: {pipeline_name}"
    
    message_parts = []
    
    # Header
    if is_success:
        message_parts.append(f"Pipeline '{pipeline_name}' completed successfully!")
    else:
        message_parts.append(f"Pipeline '{pipeline_name}' failed.")
        if error_message:
            message_parts.append(f"\nError: {error_message}")
    
    message_parts.append("")
    
    # Summary
    message_parts.append("Summary:")
    message_parts.append(f"- Total Stages: {len(stage_results)}")
    
    if validation:
        estimated_records = validation.get('estimated_records', 'N/A')
        estimated_cost = validation.get('estimated_cost_usd', 'N/A')
        message_parts.append(f"- Estimated Records Processed: {estimated_records}")
        message_parts.append(f"- Estimated Cost: ${estimated_cost}")
    
    message_parts.append("")
    
    # Stage details
    if stage_results:
        message_parts.append("Stage Results:")
        for idx, stage_result in enumerate(stage_results, 1):
            stage_name = stage_result.get('stage_name', f'Stage {idx}')
            message_parts.append(f"\n{idx}. {stage_name}")
            
            if 'output_paths' in stage_result:
                output_paths = stage_result['output_paths']
                if isinstance(output_paths, list) and output_paths:
                    message_parts.append(f"   Outputs: {len(output_paths)} file(s)")
    
    message_parts.append("")
    
    # Output files with presigned URLs
    if is_success and presigned_urls:
        message_parts.append("Output Files:")
        message_parts.append("")
        
        for idx, url_info in enumerate(presigned_urls, 1):
            path = url_info['path']
            url = url_info.get('url')
            expires = url_info.get('expires')
            error = url_info.get('error')
            
            message_parts.append(f"{idx}. {path}")
            
            if url:
                message_parts.append(f"   Download: {url}")
                message_parts.append(f"   Expires: {expires}")
            elif error:
                message_parts.append(f"   Error: {error}")
            
            message_parts.append("")
    
    message = "\n".join(message_parts)
    
    return subject, message


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Send pipeline completion notification.
    
    Expected event structure:
    {
        "pipeline_name": "my-pipeline",
        "stage_results": [
            {
                "stage_name": "stage1",
                "output_paths": ["s3://bucket/output1.parquet"]
            }
        ],
        "validation": {
            "estimated_records": 1000,
            "estimated_cost_usd": 0.50
        },
        "presigned_url_expiry_days": 7,
        "status": "SUCCESS" or "FAILED",
        "error_message": "..." (if failed)
    }
    
    Returns:
        Notification status
    """
    try:
        pipeline_name = event.get('pipeline_name', 'Unnamed Pipeline')
        stage_results = event.get('stage_results', [])
        validation = event.get('validation', {})
        expiry_days = event.get('presigned_url_expiry_days', 7)
        status = event.get('status', 'SUCCESS')
        error_message = event.get('error_message')
        
        is_success = status == 'SUCCESS'
        
        logger.info(f"Sending notification for pipeline: {pipeline_name} (status: {status})")
        
        # Collect all output paths
        all_output_paths = []
        for stage_result in stage_results:
            output_paths = stage_result.get('output_paths', [])
            if isinstance(output_paths, list):
                all_output_paths.extend(output_paths)
        
        logger.info(f"Found {len(all_output_paths)} output files")
        
        # Generate presigned URLs
        presigned_urls = []
        if is_success and all_output_paths:
            presigned_urls = generate_presigned_urls(all_output_paths, expiry_days)
        
        # Format message
        subject, message = format_notification_message(
            pipeline_name=pipeline_name,
            stage_results=stage_results,
            presigned_urls=presigned_urls,
            validation=validation,
            is_success=is_success,
            error_message=error_message
        )
        
        # Publish to SNS
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if not topic_arn:
            logger.error("SNS_TOPIC_ARN environment variable not set")
            raise ValueError("SNS_TOPIC_ARN not configured")
        
        logger.info(f"Publishing to SNS topic: {topic_arn}")
        
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        
        logger.info(f"Notification sent successfully. MessageId: {response['MessageId']}")
        
        return {
            'notification_sent': True,
            'message_id': response['MessageId'],
            'output_count': len(all_output_paths)
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
        raise
