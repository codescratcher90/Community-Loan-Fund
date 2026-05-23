"""
Login Handler
"""
import json
from datetime import datetime
from decimal import Decimal
from config import config
from config.otp import OTPType, EMAIL_OTP_TYPES
from utils import (
    UserDB,
    RefreshTokenDB,
    LoginAttemptDB,
    VerificationCodeDB,
    verify_password,
    generate_access_token,
    generate_refresh_token,
    create_otp_record,
    send_email_otp,
    send_sms_otp,
    mask_email,
    mask_phone,
    normalize_phone,
    check_resend_cooldown,
    login_success_response,
    error_response,
    get_setting,
)
from utils.schema_validator import validate_request_body
from utils.schemas import login_schema
from middleware import login_rate_limit


def _try_resend_otp(user_id: str, otp_type: str, contact: str) -> str:
    """
    Attempt to resend an OTP if cooldown has passed.
    Returns the masked contact string.
    """
    existing = VerificationCodeDB.get_code(user_id, otp_type)
    can_resend = True
    if existing:
        can_resend, _ = check_resend_cooldown(existing)

    if can_resend:
        record = create_otp_record(user_id, otp_type, contact)
        VerificationCodeDB.create_code(record)
        if otp_type in EMAIL_OTP_TYPES:
            send_email_otp(contact, record['code'], otp_type)
            return mask_email(contact)
        else:
            send_sms_otp(contact, record['code'], otp_type)
            return mask_phone(contact)

    if otp_type in EMAIL_OTP_TYPES:
        return mask_email(contact)
    return mask_phone(contact)


@login_rate_limit()
@validate_request_body(login_schema)
def login(event, context):
    """
    POST /auth/login
    Login with email or phone + password.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')

        raw_email = body.get('email', '').lower().strip() if body.get('email') else None
        raw_phone = normalize_phone(body.get('phone', '').strip()) if body.get('phone') else None
        password  = body['password']

        # Look up user
        user = None
        login_via = None
        login_contact = None

        if raw_email:
            user = UserDB.get_user_by_email(raw_email)
            login_via = 'email'
            login_contact = raw_email
        elif raw_phone:
            user = UserDB.get_user_by_phone(raw_phone)
            login_via = 'phone'
            login_contact = raw_phone

        if not user:
            LoginAttemptDB.record_attempt(ip_address, login_contact or '', success=False)
            return error_response("Invalid credentials", status_code=401)

        # Settings
        max_failed = get_setting('max_failed_login_attempts', 5)
        lockout_minutes = get_setting('account_lockout_duration_minutes', 30)
        email_verification_required = get_setting('email_verification_required', True)

        # Auto-unlock check
        if user.get('is_locked', False):
            if UserDB.should_auto_unlock(user, lockout_minutes):
                UserDB.unlock_account(user['user_id'])
                user['is_locked'] = False
                user['failed_login_attempts'] = 0
            else:
                msg = (
                    "Account is permanently locked. Contact support."
                    if lockout_minutes == 0
                    else "Account is locked due to too many failed login attempts. Try again later."
                )
                return error_response(msg, status_code=403)

        # Verification check — only for the contact method used to log in
        if email_verification_required:
            if login_via == 'email' and not user.get('email_verified', False):
                masked = _try_resend_otp(user['user_id'], OTPType.REGISTRATION_EMAIL, login_contact)
                return error_response(
                    "Email address not verified. A new verification code has been sent.",
                    status_code=403,
                    error_code="VERIFICATION_REQUIRED",
                    error_details={
                        'verification_required': True,
                        'otp_type': OTPType.REGISTRATION_EMAIL,
                        'sent_to': masked,
                    },
                )
            if login_via == 'phone' and not user.get('phone_verified', False):
                masked = _try_resend_otp(user['user_id'], OTPType.REGISTRATION_PHONE, login_contact)
                return error_response(
                    "Phone number not verified. A new verification code has been sent.",
                    status_code=403,
                    error_code="VERIFICATION_REQUIRED",
                    error_details={
                        'verification_required': True,
                        'otp_type': OTPType.REGISTRATION_PHONE,
                        'sent_to': masked,
                    },
                )

        # Password check
        if not verify_password(password, user['password']):
            failed = UserDB.increment_failed_attempts(user['user_id'])
            if failed >= max_failed:
                UserDB.lock_account(user['user_id'])
                msg = (
                    f"Account permanently locked after {max_failed} failed attempts. Contact support."
                    if lockout_minutes == 0
                    else f"Account locked for {lockout_minutes} minutes after {max_failed} failed attempts."
                )
                return error_response(msg, status_code=403)

            LoginAttemptDB.record_attempt(ip_address, login_contact, success=False)
            remaining = max_failed - failed
            return error_response(
                f"Invalid credentials. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                status_code=401,
            )

        # Successful login
        UserDB.reset_failed_attempts(user['user_id'])
        LoginAttemptDB.record_attempt(ip_address, login_contact, success=True)

        access_token = generate_access_token(user['user_id'], user.get('email', ''), user['role'])
        refresh_token = generate_refresh_token(user['user_id'])

        expires_at = int(datetime.utcnow().timestamp() + config.REFRESH_TOKEN_EXPIRY)
        RefreshTokenDB.create_token({
            'token':      refresh_token,
            'user_id':    user['user_id'],
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': Decimal(str(expires_at)),
        })

        return login_success_response(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=config.ACCESS_TOKEN_EXPIRY,
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response("Login failed", status_code=500)
