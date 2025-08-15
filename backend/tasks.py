from celery import Celery
import boto3
import os
from dotenv import load_dotenv
from utils.llamaindex_utils import chunk_faq_recursive
from utils.db_actions import save_chunks_to_db
import uuid

load_dotenv()

celery_app = Celery("tasks", broker=os.getenv("RABBITMQ_BROKER"))

@celery_app.task
def process_s3_file(bucket, key):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    print(f"✅ Texto procesado:\n{content[:200]}...")

    chunks = chunk_faq_recursive(content)
    print(f"✅ Chunks generados: {len(chunks)}")

    doc_id = str(uuid.uuid4())  # ID único del documento
    print(f"📥 Guardando chunks en PostgreSQL con doc_id = {doc_id}...")
    save_chunks_to_db(chunks, doc_id)
    print("✅ Chunks guardados con éxito.")