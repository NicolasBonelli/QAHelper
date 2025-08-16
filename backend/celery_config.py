"""
Celery configuration file for Windows compatibility
"""
import os
import platform
from dotenv import load_dotenv

load_dotenv()

# Base configuration for all platforms
BASE_CONFIG = {
    'broker_url': os.getenv("RABBITMQ_BROKER", "amqp://guest:guest@localhost:5672//"),
    'result_backend': os.getenv("CELERY_RESULT_BACKEND", "rpc://"),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'worker_disable_rate_limits': True,
    'worker_max_tasks_per_child': 1000,
    'worker_max_memory_per_child': 200000,  # 200MB
    'broker_connection_retry_on_startup': True,
    'broker_connection_max_retries': 10,
    'result_expires': 3600,  # 1 hour
    'task_soft_time_limit': 300,  # 5 minutes
    'task_time_limit': 600,  # 10 minutes
    'broker_heartbeat': 10,
    'broker_connection_timeout': 30,
    'broker_connection_retry': True,
    'broker_connection_max_retries': 10,
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    'event_queue_expires': 60,
    'worker_cancel_long_running_tasks_on_connection_loss': True,
}

# Windows-specific configuration
WINDOWS_CONFIG = {
    **BASE_CONFIG,
    'worker_pool': 'solo',  # Use solo pool on Windows to avoid multiprocessing issues
    'worker_pool_restarts': True,
    'worker_direct': True,
    'worker_redirect_stdouts': False,
    'worker_redirect_stdouts_level': 'WARNING',
}

# Unix/Linux configuration
UNIX_CONFIG = {
    **BASE_CONFIG,
    'worker_pool': 'prefork',  # Use prefork pool on Unix systems
    'worker_concurrency': 4,  # Number of worker processes
}

def get_celery_config():
    """Get the appropriate Celery configuration based on the platform"""
    if platform.system() == "Windows":
        return WINDOWS_CONFIG
    else:
        return UNIX_CONFIG

# Export the configuration
CELERY_CONFIG = get_celery_config()
