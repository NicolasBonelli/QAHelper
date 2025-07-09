from celery import Celery
import boto3
import os
from dotenv import load_dotenv

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

    # Aquí llama al código de LLM de tu compañero
    # Por ejemplo:
    #process_pdf_from_s3(content)  # <-- Ajusta los argumentos según lo que necesite su función