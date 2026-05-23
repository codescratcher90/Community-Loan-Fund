"""
Registration Handlers
"""
import uuid
import json
import secrets
from datetime import datetime
from config import config, VALID_ROLES
from config.otp import OTPType, EMAIL_OTP_TYPES, PHONE_OTP_TYPES
from utils import (
    UserDB,
    VerificationCodeDB,
    hash_password,
    create_otp_record,
    send_email_otp,
    send_sms_otp,
    mask_email,
    mask_phone,
    normalize_phone,
    success_response,
    error_response,
    get_setting
)
from utils.schema_validator import validate_request_body
from utils.schemas import registration_schema, master_registration_schema
from utils.validators import validate_email, validate_phone
from middleware import register_rate_limit


def _send_registration_otp(user_id: str, otp_type: str, contact: str) -> bool:
    """Create and send a registration OTP. Returns True on success."""
    record = create_otp_record(user_id, otp_type, contact)
    VerificationCodeDB.create_code(record)
    if otp_type in EMAIL_OTP_TYPES:
        return send_email_otp(contact, record['code'], otp_type)
    return send_sms_otp(contact, record['code'], otp_type)


@register_rate_limit()
@validate_request_body(registration_schema)
def register(event, context):
    """
    POST /auth/register
    Register a new user with email, phone, or both.
    """
    try:
        allow_public_signup = get_setting('allow_public_signup', True)
        if not allow_public_signup:
            return error_response("Public signup is currently disabled", status_code=403)

        body = json.loads(event.get('body', '{}'))

        email = body.get('email', '').lower().strip() or None
        phone = normalize_phone(body.get('phone', '').strip()) if body.get('phone') else None
        password = body['password']
        first_name = body['first_name'].strip()
        last_name = body['last_name'].strip()

        # Uniqueness checks
        if email:
            if UserDB.get_user_by_email(email):
                return error_response("Email already registered", status_code=409)
        if phone:
            if UserDB.get_user_by_phone(phone):
                return error_response("Phone number already registered", status_code=409)

        require_otp = get_setting('require_otp_on_registration', True)
        default_role = get_setting('default_public_role', 'customer')

        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        user_data = {
            'user_id':              user_id,
            'first_name':           first_name,
            'last_name':            last_name,
            'password':             hash_password(password),
            'role':                 default_role,
            'tenant_id':            None,
            'email_verified':       not require_otp and bool(email),
            'phone_verified':       not require_otp and bool(phone),
            'is_locked':            False,
            'failed_login_attempts': 0,
            'created_at':           now,
            'updated_at':           now,
        }
        if email:
            user_data['email'] = email
        if phone:
            user_data['phone'] = phone

        UserDB.create_user(user_data)

        # Send OTPs if required
        verification_sent = []
        if require_otp:
            if email:
                if not _send_registration_otp(user_id, OTPType.REGISTRATION_EMAIL, email):
                    UserDB.delete_user(user_id)
                    return error_response(
                        "Registration failed: could not send verification email. "
                        "Please check your email address and try again.",
                        status_code=500,
                    )
                verification_sent.append(f"email ({mask_email(email)})")

            if phone:
                if not _send_registration_otp(user_id, OTPType.REGISTRATION_PHONE, phone):
                    UserDB.delete_user(user_id)
                    return error_response(
                        "Registration failed: could not send verification SMS. "
                        "Please check your phone number and try again.",
                        status_code=500,
                    )
                verification_sent.append(f"SMS ({mask_phone(phone)})")

        if verification_sent:
            message = f"Registration successful. Verification code sent via {' and '.join(verification_sent)}."
        else:
            message = "Registration successful."

        return success_response(
            data={
                'user_id':        user_id,
                'first_name':     first_name,
                'last_name':      last_name,
                'email':          mask_email(email) if email else None,
                'phone':          mask_phone(phone) if phone else None,
                'role':           default_role,
                'email_verified': user_data['email_verified'],
                'phone_verified': user_data['phone_verified'],
                'created_at':     now,
            },
            message=message,
            status_code=201,
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return error_response("Registration failed", status_code=500)


@register_rate_limit()
@validate_request_body(master_registration_schema)
def register_master(event, context):
    """
    POST /auth/register-master
    Register a master user (requires secret key).
    """
    try:
        body = json.loads(event.get('body', '{}'))

        if not config.MASTER_SECRET_KEY:
            return error_response("Master registration is not configured", status_code=500)

        secret_key = body.get('secret_key', '').strip()
        if not secret_key or not secrets.compare_digest(secret_key, config.MASTER_SECRET_KEY.strip()):
            return error_response("Invalid master secret key", status_code=403)

        email = body['email'].lower().strip()
        password = body['password']
        first_name = body['first_name'].strip()
        last_name = body['last_name'].strip()
        phone = normalize_phone(body['phone'].strip()) if body.get('phone') else None

        if UserDB.get_user_by_email(email):
            return error_response("Email already registered", status_code=409)
        if phone and UserDB.get_user_by_phone(phone):
            return error_response("Phone number already registered", status_code=409)

        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        user_data = {
            'user_id':              user_id,
            'email':                email,
            'password':             hash_password(password),
            'first_name':           first_name,
            'last_name':            last_name,
            'role':                 'master',
            'tenant_id':            None,
            'email_verified':       True,
            'phone_verified':       bool(phone),
            'is_locked':            False,
            'failed_login_attempts': 0,
            'created_at':           now,
            'updated_at':           now,
        }
        if phone:
            user_data['phone'] = phone

        UserDB.create_user(user_data)

        return success_response(
            data={
                'user_id':    user_id,
                'email':      email,
                'first_name': first_name,
                'last_name':  last_name,
                'phone':      phone,
                'role':           'master',
                'email_verified': True,
                'phone_verified': bool(phone),
                'created_at':     now,
            },
            message="Master user created successfully",
            status_code=201,
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Master registration error: {str(e)}")
        return error_response("Master registration failed", status_code=500)
