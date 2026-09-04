# ============================================================
# backend/config.py
# ============================================================
import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Config:
    # Database
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', 5432))
    DB_NAME: str = os.getenv('DB_NAME', 'cloudcloner')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'cloner123!')
    
    # Redis
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    
    # Celery
    CELERY_BROKER_URL: str = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
    CELERY_RESULT_BACKEND: str = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
    
    # API
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-this-in-production-6767')
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Cloud API Keys
    AWS_KEYS: Dict = {
        'access_key': os.getenv('AWS_ACCESS_KEY', ''),
        'secret_key': os.getenv('AWS_SECRET_KEY', ''),
        'regions': ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
    }
    
    GCP_KEYS: Dict = {
        'project_id': os.getenv('GCP_PROJECT_ID', ''),
        'credentials_path': os.getenv('GCP_CREDENTIALS', '')
    }
    
    AZURE_KEYS: Dict = {
        'tenant_id': os.getenv('AZURE_TENANT_ID', ''),
        'client_id': os.getenv('AZURE_CLIENT_ID', ''),
        'client_secret': os.getenv('AZURE_CLIENT_SECRET', '')
    }
    
    # Hacking Tools
    TOOL_PATHS: Dict = {
        'nmap': '/usr/bin/nmap',
        'masscan': '/usr/bin/masscan',
        'metasploit': '/usr/share/metasploit-framework/',
        'sqlmap': '/usr/bin/sqlmap',
        'hydra': '/usr/bin/hydra',
        'aircrack': '/usr/bin/aircrack-ng',
        'hashcat': '/usr/bin/hashcat'
    }
    
    # Payload Storage
    PAYLOAD_STORAGE: str = '/var/lib/cloudcloner/payloads/'
    LOG_PATH: str = '/var/log/cloudcloner/'
    
    # OPSEC
    PROXY_CHAINS: List[str] = [
        'socks5://127.0.0.1:9050',  # TOR
        'socks5://127.0.0.1:1080',  # SSH Tunnel
    ]
    USE_TOR: bool = True
    ROTATE_USER_AGENT: bool = True
