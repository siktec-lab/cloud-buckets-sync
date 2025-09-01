"""
S3 client manager for handling dual S3 connections and operations.
"""
import time
from typing import Iterator, Dict, Any, BinaryIO, Optional
from io import BytesIO
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from loguru import logger

from ..models.config import S3Config


class S3Object:
    """Represents an S3 object with metadata."""
    
    def __init__(self, key: str, size: int, last_modified, etag: str, storage_class: str = 'STANDARD'):
        self.key = key
        self.size = size
        self.last_modified = last_modified
        self.etag = etag
        self.storage_class = storage_class


class S3Manager:
    """Manages S3 operations for customer bucket only."""
    
    def __init__(self, customer_config: S3Config):
        """Initialize S3Manager with customer configuration."""
        self.customer_config = customer_config
        
        # Initialize S3 client
        self.customer_client = self._create_s3_client(customer_config)
        
        logger.info("S3Manager initialized with customer configuration")
    
    def _create_s3_client(self, config: S3Config):
        """Create an S3 client from configuration."""
        try:
            client = boto3.client(
                's3',
                endpoint_url=config.endpoint,
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
                region_name=config.region or 'us-east-1'
            )
            logger.debug(f"Created S3 client for endpoint: {config.endpoint}")
            return client
        except Exception as e:
            logger.error(f"Failed to create S3 client for {config.endpoint}: {e}")
            raise
    
    def _retry_operation(self, operation, max_retries: int = 3, backoff_factor: float = 1.0):
        """Execute an operation with exponential backoff retry logic."""
        for attempt in range(max_retries):
            try:
                return operation()
            except (ClientError, EndpointConnectionError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Operation failed after {max_retries} attempts: {e}")
                    raise
                
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def list_objects(self) -> Iterator[S3Object]:
        """
        List all objects in the customer bucket.
            
        Yields:
            S3Object: Objects in the bucket
        """
        client, bucket = self.customer_client, self.customer_config.bucket
        
        def _list_operation():
            paginator = client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        yield S3Object(
                            key=obj['Key'],
                            size=obj['Size'],
                            last_modified=obj['LastModified'],
                            etag=obj['ETag'].strip('"'),
                            storage_class=obj.get('StorageClass', 'STANDARD')
                        )
        
        try:
            yield from self._retry_operation(_list_operation)
        except Exception as e:
            logger.error(f"Failed to list objects in customer bucket: {e}")
            raise
    
    def get_object_stream(self, key: str) -> BinaryIO:
        """
        Get an object as a binary stream from customer bucket.
        
        Args:
            key: Object key in the bucket
            
        Returns:
            BinaryIO: Stream of the object data
        """
        client, bucket = self.customer_client, self.customer_config.bucket
        
        def _get_operation():
            response = client.get_object(Bucket=bucket, Key=key)
            return response['Body']
        
        try:
            stream = self._retry_operation(_get_operation)
            logger.debug(f"Retrieved object stream for key: {key} from customer bucket")
            return stream
        except Exception as e:
            logger.error(f"Failed to get object stream for key {key} from customer bucket: {e}")
            raise
    
    def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get metadata for an object without downloading the content.
        
        Args:
            key: Object key in the bucket
            
        Returns:
            Dict containing object metadata
        """
        client, bucket = self.customer_client, self.customer_config.bucket
        
        def _head_operation():
            response = client.head_object(Bucket=bucket, Key=key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"'),
                'content_type': response.get('ContentType', 'binary/octet-stream'),
                'metadata': response.get('Metadata', {}),
                'storage_class': response.get('StorageClass', 'STANDARD')
            }
        
        try:
            metadata = self._retry_operation(_head_operation)
            logger.debug(f"Retrieved metadata for key: {key} from customer bucket")
            return metadata
        except Exception as e:
            logger.error(f"Failed to get metadata for key {key} from customer bucket: {e}")
            raise
    

    
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in the customer bucket.
        
        Args:
            key: Object key to check
            
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            self.get_object_metadata(key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to customer S3 service.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.customer_client.head_bucket(Bucket=self.customer_config.bucket)
            logger.info("Customer S3 connection test successful")
            return True
        except Exception as e:
            logger.error(f"Customer S3 connection test failed: {e}")
            return False