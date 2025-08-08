import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
INSTANCE_PATH = BASE_DIR / 'instance'
class Config:
    SECRET_KEY ='secret-key'
    ADMIN_PASSWORD ='admin'
    PORT=5000
    DATABASE_PATH = INSTANCE_PATH / 'servers.db'
    SCHEMA_PATH = BASE_DIR / 'schema.sql'
    REGISTRATION_LIMITS = {
        'MAX_REQUESTS_PER_DAY': 200,  # Макс. заявок в сутки
        'MIN_SECONDS_BETWEEN': 60   # секунд между заявками
    }