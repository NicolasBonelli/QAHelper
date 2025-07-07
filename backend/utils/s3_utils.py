import boto3
from datetime import datetime

def upload_to_s3(file, bucket_name, filename):
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_name = f"docs/{timestamp}_{filename}"
    s3.upload_fileobj(file, bucket_name, object_name)
    return object_name
