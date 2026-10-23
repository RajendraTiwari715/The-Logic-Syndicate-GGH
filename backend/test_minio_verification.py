import sys
import os
import io
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.storage import storage_client
from app.core.config import settings

def verify_minio():
    print("Testing MinIO...")
    try:
        client = storage_client.get_client()
        bucket_name = "ibvap-evidence"
        
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Bucket {bucket_name} created.")
        else:
            print(f"Bucket {bucket_name} exists.")

        test_data = b"Testing Minio Upload..."
        test_hash = hashlib.sha256(test_data).hexdigest()
        object_name = "test_evidence.txt"

        # Upload
        print("Uploading data...")
        client.put_object(
            bucket_name,
            object_name,
            data=io.BytesIO(test_data),
            length=len(test_data),
            content_type="text/plain",
            metadata={"x-amz-meta-sha256": test_hash}
        )
        print("Upload successful.")

        # Exists/Stat
        print("Checking existence...")
        stat = client.stat_object(bucket_name, object_name)
        print(f"Object stat: {stat.size} bytes, matches size: {stat.size == len(test_data)}")
        metadata_hash = stat.metadata.get('x-amz-meta-sha256') or stat.metadata.get('X-Amz-Meta-Sha256')
        print(f"Metadata Hash stored: {metadata_hash}")

        # Retrieve
        print("Retrieving data...")
        response = client.get_object(bucket_name, object_name)
        downloaded = response.read()
        response.close()
        response.release_conn()
        
        down_hash = hashlib.sha256(downloaded).hexdigest()
        print(f"Downloaded Hash matches: {down_hash == test_hash}")

        print("ALL MINIO VERIFICATION TESTS SUCCESSFUL.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    verify_minio()
