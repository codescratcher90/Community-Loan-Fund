"""
Application Settings Management
Handles reading and caching settings from DynamoDB
"""
import boto3
from decimal import Decimal
from typing import Any, Dict, Optional
from config import config

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
settings_table = dynamodb.Table(config.APP_SETTINGS_TABLE)

# In-memory cache for settings (Lambda container reuse)
_settings_cache: Dict[str, Any] = {}
_cache_initialized = False

# Default settings for Phase 1
DEFAULT_SETTINGS = {
    # Registration & User Creation
    'allow_public_signup': True,
    'allow_adding_new_users': True,
    'require_otp_on_registration': True,
    'email_verification_required': True,
    'default_public_role': 'customer',

    # Password Requirements
    'min_password_length': 4,

    # Account Security
    'max_failed_login_attempts': 5,
    'account_lockout_duration_minutes': 30,  # 0 = permanent lock

    # Settings metadata
    '_version': '1.0',
    '_initialized': True
}


def _convert_dynamodb_types(value: Any) -> Any:
    """Convert DynamoDB Decimal types to native Python types"""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def initialize_settings():
    """
    Initialize settings table with default values if not already initialized
    This should be called once during deployment or first run
    """
    try:
        # Check if settings are already initialized
        response = settings_table.get_item(Key={'setting_key': '_initialized'})
        if 'Item' in response:
            print("[INFO] Settings already initialized")
            return

        # Initialize all default settings
        print("[INFO] Initializing default settings...")
        for key, value in DEFAULT_SETTINGS.items():
            settings_table.put_item(Item={
                'setting_key': key,
                'setting_value': value,
                'setting_type': type(value).__name__
            })

        print("[INFO] Default settings initialized successfully")

    except Exception as e:
        print(f"[ERROR] Failed to initialize settings: {str(e)}")
        raise


def load_settings() -> Dict[str, Any]:
    """
    Load all settings from DynamoDB into cache
    Returns dict of setting_key -> setting_value
    """
    global _settings_cache, _cache_initialized

    try:
        # Scan all settings from DynamoDB
        response = settings_table.scan()
        items = response.get('Items', [])

        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = settings_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        # Build cache
        _settings_cache = {}
        for item in items:
            key = item['setting_key']
            value = _convert_dynamodb_types(item['setting_value'])
            _settings_cache[key] = value

        _cache_initialized = True
        print(f"[INFO] Loaded {len(_settings_cache)} settings into cache")

        return _settings_cache

    except Exception as e:
        print(f"[ERROR] Failed to load settings: {str(e)}")
        # Return default settings as fallback
        return DEFAULT_SETTINGS.copy()


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a setting value by key
    Uses cache if available, otherwise loads from DynamoDB
    """
    global _cache_initialized

    # Initialize cache if needed
    if not _cache_initialized:
        load_settings()

    # Return from cache or default
    value = _settings_cache.get(key, default)

    # If not in cache and no default provided, check DEFAULT_SETTINGS
    if value is None and key in DEFAULT_SETTINGS:
        value = DEFAULT_SETTINGS[key]

    return value


def get_all_settings() -> Dict[str, Any]:
    """
    Get all settings as a dictionary
    Uses cache if available, otherwise loads from DynamoDB
    """
    global _cache_initialized

    if not _cache_initialized:
        load_settings()

    return _settings_cache.copy()


def update_setting(key: str, value: Any) -> None:
    """
    Update a single setting in DynamoDB and cache
    """
    global _settings_cache

    try:
        # Update in DynamoDB
        settings_table.put_item(Item={
            'setting_key': key,
            'setting_value': value,
            'setting_type': type(value).__name__
        })

        # Update cache
        _settings_cache[key] = value

        print(f"[INFO] Updated setting: {key} = {value}")

    except Exception as e:
        print(f"[ERROR] Failed to update setting {key}: {str(e)}")
        raise


def update_settings(settings: Dict[str, Any]) -> None:
    """
    Update multiple settings at once
    """
    for key, value in settings.items():
        update_setting(key, value)


def clear_cache():
    """
    Clear the settings cache
    Next get_setting() call will reload from DynamoDB
    """
    global _settings_cache, _cache_initialized
    _settings_cache = {}
    _cache_initialized = False
    print("[INFO] Settings cache cleared")


# Settings database interface
class AppSettingsDB:
    """Database interface for app settings"""

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return get_setting(key, default)

    @staticmethod
    def get_all_settings() -> Dict[str, Any]:
        """Get all settings"""
        return get_all_settings()

    @staticmethod
    def update_setting(key: str, value: Any) -> None:
        """Update a setting"""
        update_setting(key, value)

    @staticmethod
    def update_settings(settings: Dict[str, Any]) -> None:
        """Update multiple settings"""
        update_settings(settings)

    @staticmethod
    def initialize_settings() -> None:
        """Initialize default settings"""
        initialize_settings()

    @staticmethod
    def clear_cache() -> None:
        """Clear settings cache"""
        clear_cache()
