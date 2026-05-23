"""
User Profile Handlers
"""
import json
from datetime import datetime
from config.otp import OTPType
from utils import (
    UserDB,
    VerificationCodeDB,
    hash_password,
    validate_password,
    validate_name,
    validate_phone,
    create_otp_record,
    send_email_otp,
    send_sms_otp,
    mask_email,
    mask_phone,
    normalize_phone,
    success_response,
    error_response,
    validation_error_response,
)
from utils.schema_validator import validate_request_body
from utils.schemas import update_profile_schema
from middleware import require_auth, get_current_user


def _safe_user_response(user: dict) -> dict:
    return {
        'user_id':       user['user_id'],
        'email':         user.get('email'),
        'phone':         user.get('phone'),
        'first_name':    user['first_name'],
        'last_name':     user['last_name'],
        'role':          user['role'],
        'tenant_id':     user.get('tenant_id'),
        'email_verified': user.get('email_verified', False),
        'phone_verified': user.get('phone_verified', False),
        'is_verified':   user.get('is_verified', False),
        'is_locked':     user.get('is_locked', False),
        'created_at':    user.get('created_at'),
        'updated_at':    user.get('updated_at'),
    }


@require_auth()
def get_me(event, context):
    """
    GET /auth/me
    Get current user profile.
    """
    try:
        current_user = get_current_user(event)
        user = UserDB.get_user_by_id(current_user['user_id'])
        if not user:
            return error_response("User not found", status_code=404)

        return success_response(data=_safe_user_response(user))

    except Exception as e:
        print(f"Get profile error: {str(e)}")
        return error_response("Failed to get profile", status_code=500)


@require_auth()
@validate_request_body(update_profile_schema)
def update_me(event, context):
    """
    PUT /auth/me
    Update current user profile.
    Changing email or phone triggers an OTP verification flow instead of
    updating the field directly.
    """
    try:
        current_user = get_current_user(event)
        body = json.loads(event.get('body', '{}'))

        user = UserDB.get_user_by_id(current_user['user_id'])
        if not user:
            return error_response("User not found", status_code=404)

        updates = {}
        errors  = {}
        otp_notifications = []

        # ── Name ──────────────────────────────────────────────────────────────
        if 'first_name' in body:
            valid, error = validate_name(body['first_name'], "First name")
            if valid:
                updates['first_name'] = body['first_name'].strip()
            else:
                errors['first_name'] = error

        if 'last_name' in body:
            valid, error = validate_name(body['last_name'], "Last name")
            if valid:
                updates['last_name'] = body['last_name'].strip()
            else:
                errors['last_name'] = error

        # ── Password ──────────────────────────────────────────────────────────
        if 'password' in body:
            valid, error = validate_password(body['password'])
            if valid:
                if 'current_password' not in body:
                    errors['current_password'] = "Current password is required to change password"
                else:
                    from utils import verify_password
                    if not verify_password(body['current_password'], user['password']):
                        errors['current_password'] = "Current password is incorrect"
                    else:
                        updates['password'] = hash_password(body['password'])
            else:
                errors['password'] = error

        # ── Email change: send OTP to new address ─────────────────────────────
        if 'email' in body:
            new_email = body['email'].lower().strip()
            if new_email == user.get('email'):
                errors['email'] = "New email is the same as current email"
            else:
                existing = UserDB.get_user_by_email(new_email)
                if existing and existing['user_id'] != user['user_id']:
                    errors['email'] = "Email address is already in use"
                else:
                    otp_type = OTPType.ADD_EMAIL if not user.get('email') else OTPType.CHANGE_EMAIL
                    record = create_otp_record(user['user_id'], otp_type, new_email)
                    VerificationCodeDB.create_code(record)
                    sent = send_email_otp(new_email, record['code'], otp_type)
                    if not sent:
                        errors['email'] = "Failed to send verification email"
                    else:
                        otp_notifications.append({
                            'otp_type': otp_type,
                            'sent_to':  mask_email(new_email),
                        })

        # ── Phone change: send OTP to new number ──────────────────────────────
        if 'phone' in body:
            new_phone = normalize_phone(body['phone'].strip())
            if new_phone == user.get('phone'):
                errors['phone'] = "New phone is the same as current phone"
            else:
                existing = UserDB.get_user_by_phone(new_phone)
                if existing and existing['user_id'] != user['user_id']:
                    errors['phone'] = "Phone number is already in use"
                else:
                    otp_type = OTPType.ADD_PHONE if not user.get('phone') else OTPType.CHANGE_PHONE
                    record = create_otp_record(user['user_id'], otp_type, new_phone)
                    VerificationCodeDB.create_code(record)
                    sent = send_sms_otp(new_phone, record['code'], otp_type)
                    if not sent:
                        errors['phone'] = "Failed to send verification SMS"
                    else:
                        otp_notifications.append({
                            'otp_type': otp_type,
                            'sent_to':  mask_phone(new_phone),
                        })

        if errors:
            return validation_error_response("Validation failed", errors)

        if not updates and not otp_notifications:
            return error_response("No valid fields to update")

        if updates:
            updates['updated_at'] = datetime.utcnow().isoformat()
            updated_user = UserDB.update_user(current_user['user_id'], updates)
        else:
            updated_user = user

        response_data = _safe_user_response(updated_user)
        if otp_notifications:
            response_data['pending_verifications'] = otp_notifications

        parts = []
        if updates:
            parts.append("Profile updated")
        if otp_notifications:
            contacts = [n['sent_to'] for n in otp_notifications]
            parts.append(f"Verification code sent to {' and '.join(contacts)}")

        return success_response(
            data=response_data,
            message=". ".join(parts) + ".",
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update profile error: {str(e)}")
        return error_response("Failed to update profile", status_code=500)
