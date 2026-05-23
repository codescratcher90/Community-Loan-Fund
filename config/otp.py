"""
OTP type constants and delivery configuration.
Add new types here as new flows are introduced.
"""


class OTPType:
    # Registration — sent on first signup
    REGISTRATION_EMAIL  = 'registration_email'
    REGISTRATION_PHONE  = 'registration_phone'
    # Login flows
    LOGIN_OTP           = 'login_otp'        # passwordless / magic link
    TWO_FACTOR          = '2fa'              # second factor after password
    # Account recovery
    FORGOT_PASSWORD     = 'forgot_password'
    ACCOUNT_RECOVERY    = 'account_recovery'
    # Contact management (verify before activating)
    ADD_EMAIL           = 'add_email'
    ADD_PHONE           = 'add_phone'
    CHANGE_EMAIL        = 'change_email'
    CHANGE_PHONE        = 'change_phone'
    # Security confirmations
    SENSITIVE_ACTION    = 'sensitive_action'
    DEVICE_VERIFICATION = 'device_verification'
    DELETE_ACCOUNT      = 'delete_account'


ALL_OTP_TYPES = [
    OTPType.REGISTRATION_EMAIL,
    OTPType.REGISTRATION_PHONE,
    OTPType.LOGIN_OTP,
    OTPType.TWO_FACTOR,
    OTPType.FORGOT_PASSWORD,
    OTPType.ACCOUNT_RECOVERY,
    OTPType.ADD_EMAIL,
    OTPType.ADD_PHONE,
    OTPType.CHANGE_EMAIL,
    OTPType.CHANGE_PHONE,
    OTPType.SENSITIVE_ACTION,
    OTPType.DEVICE_VERIFICATION,
    OTPType.DELETE_ACCOUNT,
]

# OTP types delivered to email
EMAIL_OTP_TYPES = {
    OTPType.REGISTRATION_EMAIL,
    OTPType.ADD_EMAIL,
    OTPType.CHANGE_EMAIL,
    OTPType.FORGOT_PASSWORD,
    OTPType.TWO_FACTOR,
    OTPType.SENSITIVE_ACTION,
    OTPType.DELETE_ACCOUNT,
    OTPType.DEVICE_VERIFICATION,
    OTPType.ACCOUNT_RECOVERY,
}

# OTP types delivered to phone
PHONE_OTP_TYPES = {
    OTPType.REGISTRATION_PHONE,
    OTPType.ADD_PHONE,
    OTPType.CHANGE_PHONE,
}

# Seconds a user must wait before requesting another OTP of the same type
OTP_RESEND_COOLDOWN = 60
