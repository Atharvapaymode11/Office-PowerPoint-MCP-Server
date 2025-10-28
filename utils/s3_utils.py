"""
S3 utility functions for PowerPoint MCP Server
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from io import BytesIO
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class S3Handler:
    """Handle S3 operations for PowerPoint files"""
    
    def __init__(self):
        """Initialize S3 client with environment variables"""
        self.s3_enabled = os.getenv('S3_ENABLED', 'false').lower() == 'true'
        self.s3_bucket = os.getenv('S3_BUCKET_NAME')
        self.s3_prefix = os.getenv('S3_PREFIX', 'presentations/')
        self.s3_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        if self.s3_enabled:
            if not self.s3_bucket:
                raise ValueError("S3_ENABLED is true but S3_BUCKET_NAME is not set")
            
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=self.s3_region
                )
                logger.info(f"S3 handler initialized for bucket: {self.s3_bucket}")
            except NoCredentialsError:
                logger.error("AWS credentials not found")
                raise ValueError("AWS credentials not configured properly")
        else:
            self.s3_client = None
            logger.info("S3 support disabled")
    
    def upload_presentation(self, prs, filename: str) -> Dict:
        """
        Upload presentation to S3
        
        Args:
            prs: python-pptx Presentation object
            filename: Name of the file (without path)
        
        Returns:
            Dict with upload information
        """
        if not self.s3_enabled:
            raise ValueError("S3 is not enabled. Set S3_ENABLED=true")
        
        try:
            # Save to BytesIO buffer
            buffer = BytesIO()
            prs.save(buffer)
            buffer.seek(0)
            
            # Ensure filename has .pptx extension
            if not filename.endswith('.pptx'):
                filename = f"{filename}.pptx"
            
            # Create S3 key
            s3_key = f"{self.s3_prefix.rstrip('/')}/{filename}"
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                buffer,
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                }
            )
            
            s3_url = f"s3://{self.s3_bucket}/{s3_key}"
            https_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"
            
            logger.info(f"Successfully uploaded presentation to {s3_url}")
            
            return {
                "success": True,
                "s3_url": s3_url,
                "https_url": https_url,
                "bucket": self.s3_bucket,
                "key": s3_key,
                "filename": filename
            }
            
        except ClientError as e:
            error_msg = f"Failed to upload to S3: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL or None if failed
        """
        if not self.s3_enabled:
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None

# Global S3 handler instance
_s3_handler = None

def get_s3_handler() -> S3Handler:
    """Get or create global S3 handler instance"""
    global _s3_handler
    if _s3_handler is None:
        _s3_handler = S3Handler()
    return _s3_handler