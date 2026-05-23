"""
App Settings Handlers
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
from config.permissions import VALID_ROLES

ALLOWED_SETTINGS = {
    'allow_public_signup':              bool,
    'allow_adding_new_users':           bool,
    'require_otp_on_registration':      bool,
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
