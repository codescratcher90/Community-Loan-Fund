"""
Schema definitions for all API endpoints.
Each schema defines required fields, optional fields, types, and constraints.
"""

from utils.schema_validator import Schema, SchemaField
from utils.validators import validate_email, validate_password, validate_phone, validate_name
from config.permissions import VALID_ROLES


# ==================== Authentication Schemas ====================

# POST /auth/register
registration_schema = Schema({
    'email': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_email,
        description="User email address"
    ),
    'password': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_password,
        description="User password"
    ),
    'first_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'first_name'),
        description="User first name"
    ),
    'last_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'last_name'),
        description="User last name"
    ),
    'phone': SchemaField(
        field_type=str,
        required=False,
        custom_validator=validate_phone,
        description="User phone number (optional)"
    )
}, strict=True)


# POST /auth/register-master
master_registration_schema = Schema({
    'secret_key': SchemaField(
        field_type=str,
        required=True,
        min_length=1,
        description="Master secret key"
    ),
    'email': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_email,
        description="User email address"
    ),
    'password': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_password,
        description="User password"
    ),
    'first_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'first_name'),
        description="User first name"
    ),
    'last_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'last_name'),
        description="User last name"
    ),
    'phone': SchemaField(
        field_type=str,
        required=False,
        custom_validator=validate_phone,
        description="User phone number (optional)"
    )
}, strict=True)


# POST /auth/verify
verification_schema = Schema({
    'user_id': SchemaField(
        field_type=str,
        required=True,
        min_length=1,
        description="User ID"
    ),
    'code': SchemaField(
        field_type=str,
        required=True,
        pattern=r'^\d{6}$',
        description="6-digit verification code"
    ),
    'code_type': SchemaField(
        field_type=str,
        required=True,
        allowed_values=['email', 'sms'],
        description="Type of verification code"
    )
}, strict=True)


# POST /auth/login
login_schema = Schema({
    'email': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_email,
        description="User email address"
    ),
    'password': SchemaField(
        field_type=str,
        required=True,
        min_length=1,
        description="User password"
    )
}, strict=True)


# POST /auth/refresh
refresh_token_schema = Schema({
    'refresh_token': SchemaField(
        field_type=str,
        required=True,
        min_length=1,
        description="Refresh token"
    )
}, strict=True)


# POST /auth/logout
logout_schema = Schema({
    'refresh_token': SchemaField(
        field_type=str,
        required=True,
        min_length=1,
        description="Refresh token"
    )
}, strict=True)


# ==================== Profile Schemas ====================

# PUT /auth/me
update_profile_schema = Schema({
    'first_name': SchemaField(
        field_type=str,
        required=False,
        custom_validator=lambda v: validate_name(v, 'first_name'),
        description="User first name"
    ),
    'last_name': SchemaField(
        field_type=str,
        required=False,
        custom_validator=lambda v: validate_name(v, 'last_name'),
        description="User last name"
    ),
    'phone': SchemaField(
        field_type=str,
        required=False,
        custom_validator=validate_phone,
        description="User phone number"
    ),
    'password': SchemaField(
        field_type=str,
        required=False,
        custom_validator=validate_password,
        description="New password"
    ),
    'current_password': SchemaField(
        field_type=str,
        required=False,
        min_length=1,
        description="Current password (required when changing password)"
    )
}, strict=True)


# ==================== User Management Schemas ====================

# POST /users
create_user_schema = Schema({
    'email': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_email,
        description="User email address"
    ),
    'password': SchemaField(
        field_type=str,
        required=True,
        custom_validator=validate_password,
        description="User password"
    ),
    'first_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'first_name'),
        description="User first name"
    ),
    'last_name': SchemaField(
        field_type=str,
        required=True,
        custom_validator=lambda v: validate_name(v, 'last_name'),
        description="User last name"
    ),
    'phone': SchemaField(
        field_type=str,
        required=False,
        custom_validator=validate_phone,
        description="User phone number (optional)"
    ),
    'role': SchemaField(
        field_type=str,
        required=False,
        allowed_values=VALID_ROLES,
        description="User role (optional, defaults to 'staff')"
    ),
    'tenant_id': SchemaField(
        field_type=str,
        required=False,
        min_length=1,
        description="Tenant ID (required for master creating internal users)"
    )
}, strict=True)


# PUT /users/{id}/role
update_role_schema = Schema({
    'role': SchemaField(
        field_type=str,
        required=True,
        allowed_values=VALID_ROLES,
        description="New role for the user"
    ),
    'tenant_id': SchemaField(
        field_type=str,
        required=False,
        min_length=1,
        description="Tenant ID (optional, for master only)"
    )
}, strict=True)


# ==================== Settings Schemas ====================

# PUT /settings
update_settings_schema = Schema({
    'allow_public_signup': SchemaField(
        field_type=bool,
        required=False,
        description="Allow public user registration"
    ),
    'allow_adding_new_users': SchemaField(
        field_type=bool,
        required=False,
        description="Allow admins to add new users"
    ),
    'require_otp_on_registration': SchemaField(
        field_type=bool,
        required=False,
        description="Require OTP verification on registration"
    ),
    'email_verification_required': SchemaField(
        field_type=bool,
        required=False,
        description="Require email verification"
    ),
    'default_public_role': SchemaField(
        field_type=str,
        required=False,
        allowed_values=VALID_ROLES,
        description="Default role for public signups"
    ),
    'min_password_length': SchemaField(
        field_type=int,
        required=False,
        min_value=4,
        max_value=128,
        description="Minimum password length"
    ),
    'max_failed_login_attempts': SchemaField(
        field_type=int,
        required=False,
        min_value=1,
        max_value=100,
        description="Maximum failed login attempts before lockout"
    ),
    'account_lockout_duration_minutes': SchemaField(
        field_type=int,
        required=False,
        min_value=0,
        max_value=10080,
        description="Account lockout duration in minutes (0 = permanent)"
    )
}, strict=True)


# ==================== Schema Registry ====================
# Map route patterns to their schemas for easy lookup

ROUTE_SCHEMAS = {
    'POST /auth/register': registration_schema,
    'POST /auth/register-master': master_registration_schema,
    'POST /auth/verify': verification_schema,
    'POST /auth/login': login_schema,
    'POST /auth/refresh': refresh_token_schema,
    'POST /auth/logout': logout_schema,
    'PUT /auth/me': update_profile_schema,
    'POST /users': create_user_schema,
    'PUT /users/{id}/role': update_role_schema,
    'PUT /settings': update_settings_schema,
}
