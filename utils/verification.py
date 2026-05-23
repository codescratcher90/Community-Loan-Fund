"""
Verification Code Utilities
"""
import os
import secrets
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from config import config


def generate_verification_code(length: int = 6) -> str:
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def send_email_verification(email: str, code: str) -> bool:
    """Send OTP to email via AWS SES."""
    from_email = os.getenv('FROM_EMAIL')
    if not from_email:
        print("[ERROR] FROM_EMAIL environment variable not set")
        return False

    expiry_minutes = config.VERIFICATION_CODE_EXPIRY // 60

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#333">Verification Code</h2>
      <p style="color:#555">Use the code below to verify your account:</p>
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
                'Subject': {'Data': 'Your verification code'},
                'Body': {
                    'Text': {'Data': f'Your verification code is: {code}\nExpires in {expiry_minutes} minutes.'},
                    'Html': {'Data': html},
                },
            },
        )
        print(f"[INFO] Verification email sent to {email}")
        return True
    except ClientError as e:
        print(f"[ERROR] SES send failed for {email}: {e.response['Error']['Message']}")
        return False


def send_sms_verification(phone: str, code: str) -> bool:
    """Send OTP via AWS SNS — not yet implemented."""
    # TODO: implement SNS
    print(f"[STUB] SMS OTP for {phone}: {code}")
    return True


def create_verification_record(user_id: str, code_type: str) -> dict:
    """
    Create a verification code record
    Returns dict with code and expiry
    """
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(seconds=config.VERIFICATION_CODE_EXPIRY)
    
    return {
        'user_id': user_id,
        'code_type': code_type,  # 'email' or 'sms'
        'code': code,
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': expires_at.isoformat()
    }
