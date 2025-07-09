import boto3
from datetime import datetime

def upload_text_to_s3(text: str, bucket_name: str, object_name: str, aws_access_key: str, aws_secret_key: str):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    s3.put_object(Bucket=bucket_name, Key=object_name, Body=text.encode("utf-8"))