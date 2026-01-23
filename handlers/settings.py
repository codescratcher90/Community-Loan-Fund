"""
App Settings Handlers (Master only)
"""
import json
from utils import (
    AppSettingsDB,
    success_response,
    error_response,
    validation_error_response
)
from utils.schema_validator import validate_request_body
from utils.schemas import update_settings_schema
from middleware import require_auth

# Define allowed settings and their types for validation
ALLOWED_SETTINGS = {
    # Registration & User Creation
    'allow_public_signup': bool,
    'allow_adding_new_users': bool,
    'require_otp_on_registration': bool,
    'email_verification_required': bool,
    'default_public_role': str,

    # Password Requirements
    'min_password_length': int,

    # Account Security
    'max_failed_login_attempts': int,
    'account_lockout_duration_minutes': int,
}


@require_auth(required_role='master')
def get_settings(event, context):
    """
    GET /settings
    Get all application settings (master only)
    """
    try:
        # Get all settings
        settings = AppSettingsDB.get_all_settings()

        # Filter out internal settings (starting with _)
        public_settings = {
            k: v for k, v in settings.items()
            if not k.startswith('_')
        }

        return success_response(data=public_settings)

    except Exception as e:
        print(f"Get settings error: {str(e)}")
        return error_response("Failed to get settings", status_code=500)


@require_auth(required_role='master')
@validate_request_body(update_settings_schema)
def update_settings(event, context):
    """
    PUT /settings
    Update application settings (master only)
    Accepts partial updates - only updates provided settings
    """
    try:
        body = json.loads(event.get('body', '{}'))

        if not body:
            return validation_error_response("No settings provided")

        # Validate settings
        errors = {}
        validated_settings = {}

        for key, value in body.items():
            # Check if setting is allowed
            if key not in ALLOWED_SETTINGS:
                errors[key] = f"Unknown setting: {key}"
                continue

            # Check type
            expected_type = ALLOWED_SETTINGS[key]
            if not isinstance(value, expected_type):
                errors[key] = f"Invalid type. Expected {expected_type.__name__}, got {type(value).__name__}"
                continue

            # Additional validation for specific settings
            if key == 'min_password_length':
                if value < 4:
                    errors[key] = "Minimum password length must be at least 4"
                    continue
                if value > 128:
                    errors[key] = "Minimum password length cannot exceed 128"
                    continue

            if key == 'max_failed_login_attempts':
                if value < 1:
                    errors[key] = "Maximum failed login attempts must be at least 1"
                    continue
                if value > 100:
                    errors[key] = "Maximum failed login attempts cannot exceed 100"
                    continue

            if key == 'account_lockout_duration_minutes':
                if value < 0:
                    errors[key] = "Account lockout duration cannot be negative (use 0 for permanent lock)"
                    continue
                if value > 10080:  # 7 days
                    errors[key] = "Account lockout duration cannot exceed 10080 minutes (7 days)"
                    continue

            if key == 'default_public_role':
                from config import VALID_ROLES
                if value not in VALID_ROLES:
                    errors[key] = f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
                    continue

            # Setting is valid
            validated_settings[key] = value

        if errors:
            return validation_error_response("Validation failed", errors)

        # Update settings
        AppSettingsDB.update_settings(validated_settings)

        # Return updated settings
        updated_settings = {}
        for key in validated_settings:
            updated_settings[key] = AppSettingsDB.get_setting(key)

        return success_response(
            data=updated_settings,
            message=f"Successfully updated {len(updated_settings)} setting(s)"
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update settings error: {str(e)}")
        return error_response("Failed to update settings", status_code=500)
