"""
Application Configuration
"""
import os
from typing import Optional

class Config:
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'eu-north-1')

    # App Identification
    APP_NAME: str = os.getenv('APP_NAME', 'basic-auth')
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'dev')

    # Legacy support (deprecated)
    TABLE_PREFIX: str = os.getenv('DYNAMODB_TABLE_PREFIX', f"{APP_NAME}-{ENVIRONMENT}")

    # Table Names - Format: {app-name}-{environment}-{table}
    # This allows multiple deployments in the same AWS account without conflicts
    USERS_TABLE: str = f"{APP_NAME}-{ENVIRONMENT}-users"
    REFRESH_TOKENS_TABLE: str = f"{APP_NAME}-{ENVIRONMENT}-refresh_tokens"
    VERIFICATION_CODES_TABLE: str = f"{APP_NAME}-{ENVIRONMENT}-verification_codes"
    LOGIN_ATTEMPTS_TABLE: str = f"{APP_NAME}-{ENVIRONMENT}-login_attempts"
    RATE_LIMITS_TABLE: str = f"{APP_NAME}-{ENVIRONMENT}-rate_limits"
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'change-this-secret-key')
    REFRESH_TOKEN_SECRET: str = os.getenv('REFRESH_TOKEN_SECRET', 'change-this-refresh-secret')
    ACCESS_TOKEN_EXPIRY: int = int(os.getenv('ACCESS_TOKEN_EXPIRY', '1800'))  # 30 minutes
    REFRESH_TOKEN_EXPIRY: int = int(os.getenv('REFRESH_TOKEN_EXPIRY', '2592000'))  # 30 days
    
    # Master Secret
    MASTER_SECRET_KEY: str = os.getenv('MASTER_SECRET_KEY')
    
    # Verification
    VERIFICATION_CODE_EXPIRY: int = int(os.getenv('VERIFICATION_CODE_EXPIRY', '600'))  # 10 minutes
    
    # Rate Limiting
    LOGIN_RATE_LIMIT: int = int(os.getenv('LOGIN_RATE_LIMIT', '10'))  # per hour
    REGISTER_RATE_LIMIT: int = int(os.getenv('REGISTER_RATE_LIMIT', '100'))  # per hour per IP
    API_RATE_LIMIT: int = int(os.getenv('API_RATE_LIMIT', '100'))  # per minute per user
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv('MAX_FAILED_LOGIN_ATTEMPTS', '5'))
    
    # Password Requirements
    MIN_PASSWORD_LENGTH: int = 4
    
    # Email/SMS (for future use)
    EMAIL_FROM: Optional[str] = os.getenv('EMAIL_FROM')
    SMS_SENDER_ID: Optional[str] = os.getenv('SMS_SENDER_ID')

config = Config()
