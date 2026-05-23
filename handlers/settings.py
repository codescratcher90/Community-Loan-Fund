"""
App Settings and Permissions Handlers
"""
import json
from utils import (
    AppSettingsDB,
    success_response,
    error_response,
    validation_error_response,
)
from utils.schema_validator import validate_request_body
from utils.schemas import update_settings_schema
from middleware import require_auth
from config.permissions import DEFAULT_RESOURCE_PERMISSIONS, VALID_ROLES

ALLOWED_SETTINGS = {
    'allow_public_signup':              bool,
    'allow_adding_new_users':           bool,
    'require_otp_on_registration':      bool,
    'email_verification_required':      bool,
    'default_public_role':              str,
    'min_password_length':              int,
    'max_failed_login_attempts':        int,
    'account_lockout_duration_minutes': int,
}


# ═══════════════════════════════════════════════════════════════════════════
# App Settings
# ═══════════════════════════════════════════════════════════════════════════

@require_auth(resource='settings', operation='read')
def get_settings(event, context):
    """GET /settings"""
    try:
        settings = AppSettingsDB.get_all_settings()
        public_settings = {k: v for k, v in settings.items() if not k.startswith('_')}
        return success_response(data=public_settings)
    except Exception as e:
        print(f"Get settings error: {e}")
        return error_response("Failed to get settings", status_code=500)


@require_auth(resource='settings', operation='update')
@validate_request_body(update_settings_schema)
def update_settings(event, context):
    """PUT /settings — partial update, only provided keys are changed."""
    try:
        body = json.loads(event.get('body', '{}'))
        if not body:
            return validation_error_response("No settings provided")

        errors = {}
        validated = {}

        for key, value in body.items():
            if key not in ALLOWED_SETTINGS:
                errors[key] = f"Unknown setting: {key}"
                continue
            if not isinstance(value, ALLOWED_SETTINGS[key]):
                errors[key] = (
                    f"Invalid type. Expected {ALLOWED_SETTINGS[key].__name__}, "
                    f"got {type(value).__name__}"
                )
                continue
            if key == 'min_password_length' and not (4 <= value <= 128):
                errors[key] = "Must be between 4 and 128"
                continue
            if key == 'max_failed_login_attempts' and not (1 <= value <= 100):
                errors[key] = "Must be between 1 and 100"
                continue
            if key == 'account_lockout_duration_minutes' and not (0 <= value <= 10080):
                errors[key] = "Must be between 0 and 10080 (0 = permanent lock)"
                continue
            if key == 'default_public_role' and value not in VALID_ROLES:
                errors[key] = f"Must be one of: {', '.join(VALID_ROLES)}"
                continue
            validated[key] = value

        if errors:
            return validation_error_response("Validation failed", errors)

        AppSettingsDB.update_settings(validated)
        updated = {k: AppSettingsDB.get_setting(k) for k in validated}
        return success_response(
            data=updated,
            message=f"Successfully updated {len(updated)} setting(s)"
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update settings error: {e}")
        return error_response("Failed to update settings", status_code=500)


# ═══════════════════════════════════════════════════════════════════════════
# Resource Permissions
# ═══════════════════════════════════════════════════════════════════════════

@require_auth(resource='permissions', operation='read')
def get_all_permissions(event, context):
    """
    GET /settings/permissions
    Returns all resource configs stored in DynamoDB plus the seed template.
    """
    try:
        configs = AppSettingsDB.get_all_resource_configs()
        return success_response(data={
            'resources':      configs,
            'default_config': DEFAULT_RESOURCE_PERMISSIONS,
        })
    except Exception as e:
        print(f"Get permissions error: {e}")
        return error_response("Failed to get permissions", status_code=500)


@require_auth(resource='permissions', operation='read')
def get_resource_permissions(event, context):
    """GET /settings/permissions/{resource}"""
    try:
        resource = (event.get('pathParameters') or {}).get('resource')
        config = AppSettingsDB.get_resource_config(resource)
        if config is None:
            return error_response(
                f"No permission config found for resource '{resource}'. "
                "Call POST /settings/permissions/seed to initialise defaults.",
                status_code=404,
                error_code="NOT_FOUND",
            )
        return success_response(data={'resource': resource, 'operations': config})
    except Exception as e:
        print(f"Get resource permissions error: {e}")
        return error_response("Failed to get resource permissions", status_code=500)


@require_auth(resource='permissions', operation='update')
def update_resource_permissions(event, context):
    """
    PUT /settings/permissions/{resource}
    Full replace of the operations dict for a resource.
    Body: { "operation_name": ["role1", "role2"], ... }
    Empty list [] means master-only.
    """
    try:
        resource = (event.get('pathParameters') or {}).get('resource')
        if not resource:
            return error_response("Resource name is required", status_code=400)

        body = json.loads(event.get('body', '{}'))
        if not isinstance(body, dict) or not body:
            return validation_error_response(
                "Body must be a non-empty JSON object of {operation: [roles]}"
            )

        errors = {}
        validated = {}
        valid_non_master = [r for r in VALID_ROLES if r != 'master']

        for op, roles in body.items():
            if not isinstance(op, str) or not op:
                errors[str(op)] = "Operation name must be a non-empty string"
                continue
            if not isinstance(roles, list):
                errors[op] = "Value must be a list of role names"
                continue
            invalid = [r for r in roles if r not in valid_non_master]
            if invalid:
                errors[op] = (
                    f"Invalid roles: {', '.join(invalid)}. "
                    "master always has access and cannot be listed."
                )
                continue
            validated[op] = roles

        if errors:
            return validation_error_response("Invalid operations", errors)

        AppSettingsDB.set_resource_config(resource, validated)
        return success_response(
            data={'resource': resource, 'operations': validated},
            message=f"Permissions updated for resource '{resource}'",
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update resource permissions error: {e}")
        return error_response("Failed to update resource permissions", status_code=500)


@require_auth(resource='permissions', operation='seed')
def seed_permissions(event, context):
    """
    POST /settings/permissions/seed
    Writes DEFAULT_RESOURCE_PERMISSIONS to DynamoDB. Master only (operation
    'seed' is not in any resource config, so non-masters are always denied).
    Idempotent — safe to call multiple times.
    """
    try:
        result = AppSettingsDB.seed_default_permissions()
        return success_response(
            data=result,
            message=f"Seeded permissions for {len(result['seeded'])} resources",
        )
    except Exception as e:
        print(f"Seed permissions error: {e}")
        return error_response("Failed to seed permissions", status_code=500)


@require_auth(resource='permissions', operation='cache_clear')
def clear_permissions_cache(event, context):
    """
    POST /settings/permissions/cache/clear
    Clears the in-memory permission cache on this Lambda container.
    Master only. Call after manually editing DynamoDB or after updating
    permissions — forces all subsequent requests to re-read from DB.
    """
    try:
        AppSettingsDB.clear_resource_permission_cache()
        return success_response(message="Permission cache cleared")
    except Exception as e:
        print(f"Clear cache error: {e}")
        return error_response("Failed to clear permission cache", status_code=500)
