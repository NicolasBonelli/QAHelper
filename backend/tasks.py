from celery import Celery
import boto3
import os
from dotenv import load_dotenv
from backend.utils.llamaindex_utils import chunk_faq_recursive
from .celery_config import CELERY_CONFIG

load_dotenv(override=True)

# Initialize Celery with platform-specific configuration
celery_app = Celery("tasks")
celery_app.config_from_object(CELERY_CONFIG)

@celery_app.task
def process_s3_file(bucket, key):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    print(f"✅ Text processed:\n{content[:200]}...")

    # chunk_faq_recursive already handles saving chunks to the database
    doc_id = chunk_faq_recursive(content)
    print(f"✅ Processing completed with doc_id: {doc_id}")

 
@celery_app.task
def process_local_file(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"✅ Text processed:\n{content[:200]}...")

    # chunk_faq_recursive already handles saving chunks to the database
    doc_id = chunk_faq_recursive(content)
    print(f"✅ Processing completed with doc_id: {doc_id}")