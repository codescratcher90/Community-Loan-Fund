"""
OTP Verification and Resend Handlers
"""
import json
from datetime import datetime, timedelta
from config.otp import OTPType, EMAIL_OTP_TYPES, PHONE_OTP_TYPES
from utils import (
    UserDB,
    VerificationCodeDB,
    create_otp_record,
    check_resend_cooldown,
    send_email_otp,
    send_sms_otp,
    mask_email,
    mask_phone,
    normalize_phone,
    success_response,
    error_response,
)
from utils.schema_validator import validate_request_body
from utils.schemas import verification_schema, resend_otp_schema
from utils.validators import validate_email


def _compute_is_verified(user: dict, email_verified: bool = None, phone_verified: bool = None) -> bool:
    ev = email_verified if email_verified is not None else user.get('email_verified', False)
    pv = phone_verified if phone_verified is not None else user.get('phone_verified', False)
    return ev or pv


@validate_request_body(verification_schema)
def verify(event, context):
    """
    POST /auth/verify
    Verify an OTP code for any supported OTP type.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body['user_id']
        code    = body['code']
        otp_type = body['otp_type']

        # Fetch and validate the OTP record
        record = VerificationCodeDB.verify_code(user_id, otp_type, code)
        if not record:
            return error_response("Invalid or expired verification code", status_code=400)

        user = UserDB.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", status_code=404)

        updates = {'updated_at': datetime.utcnow().isoformat()}
        response_data = {'user_id': user_id, 'otp_type': otp_type}

        # ── Registration verifications ────────────────────────────────────────
        if otp_type == OTPType.REGISTRATION_EMAIL:
            updates['email_verified'] = True
            updates['is_verified'] = _compute_is_verified(user, email_verified=True)
            response_data.update({'email_verified': True, 'is_verified': updates['is_verified']})

        elif otp_type == OTPType.REGISTRATION_PHONE:
            updates['phone_verified'] = True
            updates['is_verified'] = _compute_is_verified(user, phone_verified=True)
            response_data.update({'phone_verified': True, 'is_verified': updates['is_verified']})

        # ── Add / change email ────────────────────────────────────────────────
        elif otp_type in (OTPType.ADD_EMAIL, OTPType.CHANGE_EMAIL):
            new_email = record.get('contact')
            if not new_email:
                return error_response("Verification record missing contact email", status_code=500)

            # Ensure it's not already taken by another user
            existing = UserDB.get_user_by_email(new_email)
            if existing and existing['user_id'] != user_id:
                return error_response("Email address is already in use", status_code=409)

            updates['email'] = new_email
            updates['email_verified'] = True
            updates['is_verified'] = _compute_is_verified(user, email_verified=True)
            response_data.update({
                'email': mask_email(new_email),
                'email_verified': True,
                'is_verified': updates['is_verified'],
            })

        # ── Add / change phone ────────────────────────────────────────────────
        elif otp_type in (OTPType.ADD_PHONE, OTPType.CHANGE_PHONE):
            new_phone = record.get('contact')
            if not new_phone:
                return error_response("Verification record missing contact phone", status_code=500)

            existing = UserDB.get_user_by_phone(new_phone)
            if existing and existing['user_id'] != user_id:
                return error_response("Phone number is already in use", status_code=409)

            updates['phone'] = new_phone
            updates['phone_verified'] = True
            updates['is_verified'] = _compute_is_verified(user, phone_verified=True)
            response_data.update({
                'phone': mask_phone(new_phone),
                'phone_verified': True,
                'is_verified': updates['is_verified'],
            })

        # ── Forgot password ───────────────────────────────────────────────────
        elif otp_type == OTPType.FORGOT_PASSWORD:
            # Mark that a password reset is now permitted (10-minute window).
            # A future POST /auth/reset-password endpoint checks this flag.
            reset_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            updates['password_reset_verified'] = True
            updates['password_reset_expires_at'] = reset_expires
            response_data['password_reset_expires_at'] = reset_expires

        # ── All other types (2fa, sensitive_action, etc.) ─────────────────────
        # No user field updates needed — just confirming the OTP was valid.

        UserDB.update_user(user_id, updates)

        return success_response(
            data=response_data,
            message="Verification successful",
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Verification error: {str(e)}")
        return error_response("Verification failed", status_code=500)


@validate_request_body(resend_otp_schema)
def resend_otp(event, context):
    """
    POST /auth/resend-otp
    Resend an OTP (public endpoint — user may not be authenticated yet).
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_id  = body['user_id']
        otp_type = body['otp_type']

        user = UserDB.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", status_code=404)

        existing = VerificationCodeDB.get_code(user_id, otp_type)
        if not existing:
            return error_response(
                "No pending verification found for this OTP type. "
                "Start the flow again.",
                status_code=404,
            )

        can_resend, seconds_remaining = check_resend_cooldown(existing)
        if not can_resend:
            return error_response(
                f"Please wait {seconds_remaining} seconds before requesting another code.",
                status_code=429,
            )

        contact = existing.get('contact')
        if not contact:
            return error_response(
                "Contact information not available for this OTP. "
                "Start the flow again.",
                status_code=400,
            )

        new_record = create_otp_record(user_id, otp_type, contact)
        VerificationCodeDB.create_code(new_record)

        if otp_type in EMAIL_OTP_TYPES:
            sent = send_email_otp(contact, new_record['code'], otp_type)
            masked = mask_email(contact)
        else:
            sent = send_sms_otp(contact, new_record['code'], otp_type)
            masked = mask_phone(contact)

        if not sent:
            return error_response("Failed to send verification code", status_code=500)

        return success_response(
            data={
                'user_id':       user_id,
                'otp_type':      otp_type,
                'sent_to':       masked,
                'resend_after':  new_record['resend_after'],
            },
            message="Verification code resent",
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Resend OTP error: {str(e)}")
        return error_response("Failed to resend OTP", status_code=500)
