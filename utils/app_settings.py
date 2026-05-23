"""
Application Settings Management
Handles reading and caching settings from DynamoDB.

Two separate caches live in this module:
  _settings_cache            — general app settings (allow_public_signup, etc.)
  _resource_permission_cache — resource → operations dict (who can do what)

Permission design: secure by default.
  get_resource_config() returns None if no record exists.
  has_resource_permission() treats None as denied.
  Only master bypasses all permission checks.
"""
import boto3
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from boto3.dynamodb.conditions import Attr
from config import config

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
settings_table = dynamodb.Table(config.APP_SETTINGS_TABLE)

# Cache TTL — both caches expire after this many seconds so that manual
# DynamoDB edits propagate to all warm Lambda containers automatically.
_CACHE_TTL = 60  # seconds

# ── General settings cache ────────────────────────────────────────────────
_settings_cache: Dict[str, Any] = {}
_settings_cache_expires_at: float = 0.0

# ── Resource permission cache (separate — different invalidation needs) ───
# Values: None → no record exists (deny); dict → the stored config
# Each key's expiry is stored alongside: _resource_permission_cache_expires[key]
_resource_permission_cache: Dict[str, Optional[dict]] = {}
_resource_permission_cache_expires: Dict[str, float] = {}

# Default app settings
DEFAULT_SETTINGS = {
    'allow_public_signup':              True,
    'allow_adding_new_users':           True,
    'require_otp_on_registration':      True,
    'email_verification_required':      True,
    'default_public_role':              'customer',
    'min_password_length':              4,
    'max_failed_login_attempts':        5,
    'account_lockout_duration_minutes': 30,
    '_version':     '1.0',
    '_initialized': True,
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _convert_dynamodb_types(value: Any) -> Any:
    """Convert DynamoDB Decimal types to native Python types."""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


# ═══════════════════════════════════════════════════════════════════════════
# General Settings
# ═══════════════════════════════════════════════════════════════════════════

def initialize_settings():
    """
    Seed the app_settings table with DEFAULT_SETTINGS if not already done.
    Called once on cold start; safe to call multiple times.
    Permission defaults are NOT seeded here — use POST /settings/permissions/seed.
    """
    try:
        response = settings_table.get_item(Key={'setting_key': '_initialized'})
        if 'Item' in response:
            print("[INFO] Settings already initialized")
            return

        print("[INFO] Initializing default settings...")
        for key, value in DEFAULT_SETTINGS.items():
            settings_table.put_item(Item={
                'setting_key':   key,
                'setting_value': value,
                'setting_type':  type(value).__name__,
            })
        print("[INFO] Default settings initialized successfully")

    except Exception as e:
        print(f"[ERROR] Failed to initialize settings: {e}")
        raise


def _settings_cache_expired() -> bool:
    return time.time() >= _settings_cache_expires_at


def load_settings() -> Dict[str, Any]:
    """Load all general settings from DynamoDB into cache and reset TTL."""
    global _settings_cache, _settings_cache_expires_at

    try:
        response = settings_table.scan()
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = settings_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        _settings_cache = {}
        for item in items:
            key   = item['setting_key']
            value = _convert_dynamodb_types(item['setting_value'])
            _settings_cache[key] = value

        _settings_cache_expires_at = time.time() + _CACHE_TTL
        print(f"[INFO] Loaded {len(_settings_cache)} settings into cache (TTL {_CACHE_TTL}s)")
        return _settings_cache

    except Exception as e:
        print(f"[ERROR] Failed to load settings: {e}")
        return DEFAULT_SETTINGS.copy()


def get_setting(key: str, default: Any = None) -> Any:
    if _settings_cache_expired():
        load_settings()
    value = _settings_cache.get(key, default)
    if value is None and key in DEFAULT_SETTINGS:
        value = DEFAULT_SETTINGS[key]
    return value


def get_all_settings() -> Dict[str, Any]:
    if _settings_cache_expired():
        load_settings()
    return _settings_cache.copy()


def update_setting(key: str, value: Any) -> None:
    settings_table.put_item(Item={
        'setting_key':   key,
        'setting_value': value,
        'setting_type':  type(value).__name__,
    })
    _settings_cache[key] = value
    print(f"[INFO] Updated setting: {key} = {value}")


def update_settings(settings: Dict[str, Any]) -> None:
    for key, value in settings.items():
        update_setting(key, value)


def clear_cache():
    """Force-expire the general settings cache so the next read hits DynamoDB."""
    global _settings_cache_expires_at
    _settings_cache_expires_at = 0.0
    print("[INFO] Settings cache expired")


# ═══════════════════════════════════════════════════════════════════════════
# Resource Permission System
# ═══════════════════════════════════════════════════════════════════════════

def get_resource_config(resource: str) -> Optional[dict]:
    """
    Return the full permission record for a resource from cache or DynamoDB.
    Returns None if no record exists — caller must treat as denied.
    Fails closed on DynamoDB errors.
    Cache entry expires after _CACHE_TTL seconds so direct DynamoDB edits
    propagate automatically.
    """
    cache_key = f'resource_permission:{resource}'

    if (cache_key in _resource_permission_cache
            and time.time() < _resource_permission_cache_expires.get(cache_key, 0)):
        return _resource_permission_cache[cache_key]

    try:
        response = settings_table.get_item(Key={'setting_key': cache_key})
        value = response['Item'].get('setting_value') if 'Item' in response else None
        _resource_permission_cache[cache_key] = value
        _resource_permission_cache_expires[cache_key] = time.time() + _CACHE_TTL
        return value
    except Exception as e:
        print(f"[ERROR] Failed to get resource config for '{resource}': {e}")
        return None  # fail closed


def set_resource_config(
    resource: str,
    operations: dict,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Write the resource permission record to DynamoDB.
    Preserves existing created_at, display_name, and description on update.
    Auto-clears the in-memory cache for this resource so the change takes
    effect immediately on the current Lambda container.
    """
    cache_key = f'resource_permission:{resource}'

    # Fetch existing record to preserve metadata
    existing_meta: dict = {}
    try:
        response = settings_table.get_item(Key={'setting_key': cache_key})
        if 'Item' in response:
            existing_value = response['Item'].get('setting_value', {})
            if isinstance(existing_value, dict) and 'operations' in existing_value:
                existing_meta = {
                    'created_at':   existing_value.get('created_at'),
                    'display_name': existing_value.get('display_name'),
                    'description':  existing_value.get('description'),
                }
    except Exception as e:
        print(f"[WARN] Could not fetch existing config for '{resource}': {e}")

    now = datetime.utcnow().isoformat()
    record: dict = {
        'operations': operations,
        'created_at': existing_meta.get('created_at') or now,
        'updated_at': now,
    }

    resolved_display_name = display_name if display_name is not None else existing_meta.get('display_name')
    resolved_description  = description  if description  is not None else existing_meta.get('description')
    if resolved_display_name is not None:
        record['display_name'] = resolved_display_name
    if resolved_description is not None:
        record['description'] = resolved_description

    settings_table.put_item(Item={
        'setting_key':   cache_key,
        'setting_value': record,
        'setting_type':  'map',
    })

    # Write the new value into cache immediately so this container doesn't
    # re-read from DynamoDB, and reset the TTL.
    _resource_permission_cache[cache_key] = record
    _resource_permission_cache_expires[cache_key] = time.time() + _CACHE_TTL

    return record


def has_resource_permission(resource: str, operation: str, role: str) -> bool:
    """
    Main RBAC check. Secure by default:
      - No DB record for the resource → denied
      - Operation not listed in the record → denied
      - Role not in the allowed list → denied
      - master role → always allowed (bypasses everything)
    Supports both storage formats:
      - New: {"operations": {...}, "display_name": "...", ...}
      - Legacy flat: {"list": [...], "read": [...], ...}
    """
    if role == 'master':
        return True

    config = get_resource_config(resource)
    if config is None:
        return False

    # Handle nested format {operations: {...}} and legacy flat {op: [...]}
    ops = config.get('operations', config)
    allowed_roles = ops.get(operation)
    if allowed_roles is None:
        return False

    return role in allowed_roles


def seed_default_permissions() -> dict:
    """
    Write DEFAULT_RESOURCE_PERMISSIONS to DynamoDB.
    Idempotent — overwrites any existing config.
    Called by POST /settings/permissions/seed (master only).
    """
    from config.permissions import DEFAULT_RESOURCE_PERMISSIONS
    seeded = []
    for resource, operations in DEFAULT_RESOURCE_PERMISSIONS.items():
        set_resource_config(resource, operations)
        seeded.append(resource)
        print(f"[INFO] Seeded permissions for resource: {resource}")
    return {'seeded': seeded}


def clear_resource_permission_cache() -> None:
    """Force-expire all resource permission cache entries so next reads hit DynamoDB."""
    _resource_permission_cache_expires.clear()
    print("[INFO] Resource permission cache expired")


def get_all_resource_configs() -> dict:
    """
    Return all resource permission configs currently stored in DynamoDB.
    Bypasses cache to always reflect live DB state.
    """
    try:
        response = settings_table.scan(
            FilterExpression=Attr('setting_key').begins_with('resource_permission:')
        )
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = settings_table.scan(
                FilterExpression=Attr('setting_key').begins_with('resource_permission:'),
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            items.extend(response.get('Items', []))

        return {
            item['setting_key'].replace('resource_permission:', ''): item['setting_value']
            for item in items
        }
    except Exception as e:
        print(f"[ERROR] Failed to get all resource configs: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# AppSettingsDB — static interface (keeps existing call sites working)
# ═══════════════════════════════════════════════════════════════════════════

class AppSettingsDB:

    # General settings
    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        return get_setting(key, default)

    @staticmethod
    def get_all_settings() -> Dict[str, Any]:
        return get_all_settings()

    @staticmethod
    def update_setting(key: str, value: Any) -> None:
        update_setting(key, value)

    @staticmethod
    def update_settings(settings: Dict[str, Any]) -> None:
        update_settings(settings)

    @staticmethod
    def initialize_settings() -> None:
        initialize_settings()

    @staticmethod
    def clear_cache() -> None:
        clear_cache()

    # Resource permissions
    @staticmethod
    def get_resource_config(resource: str) -> Optional[dict]:
        return get_resource_config(resource)

    @staticmethod
    def set_resource_config(
        resource: str,
        operations: dict,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        return set_resource_config(resource, operations, display_name, description)

    @staticmethod
    def has_resource_permission(resource: str, operation: str, role: str) -> bool:
        return has_resource_permission(resource, operation, role)

    @staticmethod
    def seed_default_permissions() -> dict:
        return seed_default_permissions()

    @staticmethod
    def clear_resource_permission_cache() -> None:
        clear_resource_permission_cache()

    @staticmethod
    def get_all_resource_configs() -> dict:
        return get_all_resource_configs()
