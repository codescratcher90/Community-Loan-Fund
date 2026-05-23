"""
OTP / Verification Utilities
"""
import os
import re
import secrets
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from config import config
from config.otp import OTPType, OTP_RESEND_COOLDOWN


# ── Code generation ──────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


# ── OTP record helpers ───────────────────────────────────────────────────────

def create_otp_record(user_id: str, otp_type: str, contact: str = None) -> dict:
    """
    Build an OTP record ready for DynamoDB.
    Writing this record overwrites any previous OTP for the same user+type,
    effectively invalidating the old code.

    contact — the email address or phone number the OTP will be sent to.
               Stored in the record so resend can use the same destination.
    """
    now = datetime.utcnow()
    record = {
        'user_id':      user_id,
        'code_type':    otp_type,   # DynamoDB RANGE key
        'code':         generate_otp(),
        'created_at':   now.isoformat(),
        'expires_at':   (now + timedelta(seconds=config.VERIFICATION_CODE_EXPIRY)).isoformat(),
        'resend_after': (now + timedelta(seconds=OTP_RESEND_COOLDOWN)).isoformat(),
    }
    if contact:
        record['contact'] = contact
    return record


def check_resend_cooldown(existing_record: dict) -> tuple[bool, int]:
    """
    Returns (can_resend, seconds_remaining).
    can_resend=True means the cooldown has passed and a new OTP can be issued.
    """
    resend_after_str = existing_record.get('resend_after')
    if not resend_after_str:
        return True, 0
    try:
        resend_after = datetime.fromisoformat(resend_after_str)
        now = datetime.utcnow()
        if now < resend_after:
            return False, int((resend_after - now).total_seconds())
    except (ValueError, TypeError):
        pass
    return True, 0


# ── Masking helpers (for safe display in responses) ──────────────────────────

def mask_email(email: str) -> str:
    """us***@example.com"""
    try:
        local, domain = email.split('@', 1)
        visible = min(2, len(local))
        return f"{local[:visible]}{'*' * (len(local) - visible)}@{domain}"
    except ValueError:
        return '***'


def mask_phone(phone: str) -> str:
    """Returns last 3 digits prefixed with stars: ***456"""
    if len(phone) <= 3:
        return '*' * len(phone)
    return f"{'*' * (len(phone) - 3)}{phone[-3:]}"


def normalize_phone(phone: str) -> str:
    """Strip formatting chars, keep leading +."""
    return re.sub(r'[\s\-\(\)]', '', phone)


# ── Delivery ─────────────────────────────────────────────────────────────────

_EMAIL_SUBJECTS = {
    OTPType.REGISTRATION_EMAIL:  'Verify your email address',
    OTPType.ADD_EMAIL:           'Verify your new email address',
    OTPType.CHANGE_EMAIL:        'Confirm your new email address',
    OTPType.FORGOT_PASSWORD:     'Reset your password',
    OTPType.TWO_FACTOR:          'Two-factor authentication code',
    OTPType.SENSITIVE_ACTION:    'Confirm sensitive action',
    OTPType.DELETE_ACCOUNT:      'Confirm account deletion',
    OTPType.DEVICE_VERIFICATION: 'New device verification',
    OTPType.ACCOUNT_RECOVERY:    'Account recovery code',
    OTPType.LOGIN_OTP:           'Your login code',
}


def send_email_otp(email: str, code: str, otp_type: str) -> bool:
    """Send OTP via AWS SES. Returns True on success."""
    from_email = os.getenv('FROM_EMAIL')
    if not from_email:
        print("[ERROR] FROM_EMAIL environment variable not set")
        return False

    subject = _EMAIL_SUBJECTS.get(otp_type, 'Your verification code')
    expiry_minutes = config.VERIFICATION_CODE_EXPIRY // 60

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#333">{subject}</h2>
      <p style="color:#555">Your verification code is:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:8px;
                  padding:16px 24px;background:#f4f4f4;border-radius:8px;
                  text-align:center;color:#111">{code}</div>
      <p style="color:#888;font-size:13px;margin-top:24px">
        Expires in <strong>{expiry_minutes} minutes</strong>.
        If you did not request this, please ignore this email.
      </p>
    </div>
    """

    try:
        boto3.client('ses').send_email(
            Source=from_email,
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': f'Your code: {code} (expires in {expiry_minutes} min)'},
                    'Html': {'Data': html},
                },
            },
        )
        print(f"[INFO] OTP email ({otp_type}) sent to {email}")
        return True
    except ClientError as e:
        print(f"[ERROR] SES failed for {email}: {e.response['Error']['Message']}")
        return False


def send_sms_otp(phone: str, code: str, otp_type: str) -> bool:
    """Send OTP via SMS. SNS integration — not yet implemented."""
    # TODO: implement SNS
    print(f"[STUB] SMS OTP ({otp_type}) for {phone}: {code}")
    return True


# ── Backward-compatible aliases (used by existing callers) ───────────────────

def generate_verification_code(length: int = 6) -> str:
    return generate_otp(length)


def send_email_verification(email: str, code: str) -> bool:
    return send_email_otp(email, code, OTPType.REGISTRATION_EMAIL)


def send_sms_verification(phone: str, code: str) -> bool:
    return send_sms_otp(phone, code, OTPType.REGISTRATION_PHONE)


def create_verification_record(user_id: str, code_type: str) -> dict:
    return create_otp_record(user_id, code_type)
