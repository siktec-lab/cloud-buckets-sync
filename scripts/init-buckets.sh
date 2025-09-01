#!/bin/bash

# Wait for MinIO services to be ready
echo "Waiting for MinIO services to start..."
sleep 10

# Configure MinIO client aliases
mc alias set customer http://minio-customer:9000 minioadmin minioadmin
mc alias set target http://minio-target:9000 minioadmin minioadmin

# Create buckets
echo "Creating buckets..."
mc mb customer/customer-bucket --ignore-existing
mc mb target/target-bucket --ignore-existing

# Copy test data if available
if [ -d /test-data ]; then
    echo "Copying test data to customer bucket..."
    mc cp --recursive /test-data/ customer/customer-bucket/
fi

echo "MinIO initialization complete"