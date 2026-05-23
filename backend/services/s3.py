import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional

def get_s3_client():
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not aws_access_key or not aws_secret_key:
        return None
        
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=region
    )

def generate_presigned_url(filename: str, expiration: int = 3600) -> Optional[Dict[str, str]]:
    """
    Generate a presigned S3 URL to upload a file directly from the frontend (HTTP PUT).
    """
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "us-east-1")
    s3_client = get_s3_client()
    
    if not s3_client or not bucket_name:
        # Fallback helper for local testing without S3 configuration
        return {
            "upload_url": f"http://localhost:8000/api/mock-upload?filename={filename}",
            "file_url": f"http://localhost:8000/static/uploads/{filename}",
            "warning": "AWS credentials not configured. Using local mock upload."
        }
        
    try:
        response = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': filename,
                'ContentType': 'image/jpeg' # Adjust if needed or make dynamic
            },
            ExpiresIn=expiration
        )
        
        file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename}"
        
        return {
            "upload_url": response,
            "file_url": file_url
        }
    except ClientError as e:
        print(f"Error generating S3 presigned URL: {e}")
        return None
