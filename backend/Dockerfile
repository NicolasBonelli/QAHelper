FROM python:3.11-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get clean

# Copy requirements.txt from project root
COPY ../requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]