# Authentication Endpoints

---

## POST /auth/register

Register a new user. At least one of `email` or `phone` is required.
If `require_otp_on_registration` is enabled (default), an OTP is sent and
the account cannot log in until that contact method is verified.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | conditional | Required if no phone |
| `phone` | string | conditional | Required if no email. Formatting stripped automatically (`+12345678900` or `+1 (234) 567-8900` both work) |
| `password` | string | yes | Min length set by `min_password_length` setting (default 4, raise to 8+ for production) |
| `first_name` | string | yes | |
| `last_name` | string | yes | |

### Response `201`

Email and phone are **masked** in the response for security.

```json
{
  "success": true,
  "status_code": 201,
  "message": "Registration successful. Verification code sent via email (jo***@example.com).",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "first_name": "John",
    "last_name": "Doe",
    "email": "jo***@example.com",
    "phone": null,
    "role": "customer",
    "email_verified": false,
    "phone_verified": false,
    "created_at": "2025-05-23T10:30:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| 403 | Public signup disabled (`allow_public_signup = false`) |
| 409 | Email already registered |
| 409 | Phone already registered |
| 500 | OTP send failed (SES/SNS error) — user record is rolled back so they can retry |

### Examples

```bash
# Email only
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Phone only
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+12025550100",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Both
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "phone": "+12025550100",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

---

## POST /auth/verify

Submit a 6-digit OTP code. The `otp_type` tells the server what to do on
successful verification — mark email verified, apply a pending email change,
unlock a sensitive action, etc.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | Returned at registration or login |
| `code` | string | yes | 6-digit numeric code |
| `otp_type` | string | yes | One of the values in the table below |

### OTP Types

| `otp_type` | Use when |
|---|---|
| `registration_email` | Verifying email after registration |
| `registration_phone` | Verifying phone after registration |
| `add_email` | Confirming a new email added via PUT /auth/me |
| `change_email` | Confirming a changed email via PUT /auth/me |
| `add_phone` | Confirming a new phone added via PUT /auth/me |
| `change_phone` | Confirming a changed phone via PUT /auth/me |
| `forgot_password` | Identity check before password reset *(endpoint coming)* |
| `login_otp` | Passwordless login *(future)* |
| `2fa` | Two-factor second step *(future)* |
| `sensitive_action` | Confirming high-risk action *(future)* |
| `device_verification` | New device check *(future)* |
| `delete_account` | Confirming account deletion *(future)* |
| `account_recovery` | Recovery flow *(future)* |

### Response `200`

The response `data` shape depends on `otp_type`:

**`registration_email` / `registration_phone`**
```json
{
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "registration_email",
    "email_verified": true
  }
}
```

**`add_email` / `change_email`**
```json
{
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "change_email",
    "email": "ne***@example.com",
    "email_verified": true
  }
}
```

**`add_phone` / `change_phone`**
```json
{
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "change_phone",
    "phone": "***900",
    "phone_verified": true
  }
}
```

**`forgot_password`**
```json
{
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "forgot_password",
    "password_reset_expires_at": "2025-05-23T10:40:00.000000"
  }
}
```

**All other types**
```json
{
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "sensitive_action"
  }
}
```

### Errors

| Status | When |
|---|---|
| 400 | Invalid or expired code |
| 404 | User not found |
| 409 | New email/phone is already taken by another account |

### Examples

```bash
# Verify registration email
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "482951",
    "otp_type": "registration_email"
  }'

# Apply a pending email change
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "739012",
    "otp_type": "change_email"
  }'
```

---

## POST /auth/resend-otp

Resend a pending OTP. The code is sent to the same contact address stored
when the OTP was first created — the caller cannot redirect it elsewhere.
A 60-second cooldown is enforced between resends.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | |
| `otp_type` | string | yes | Same type as the pending OTP |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Verification code resent",
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "registration_email",
    "sent_to": "jo***@example.com",
    "resend_after": "2025-05-23T10:31:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| 404 | User not found |
| 404 | No pending OTP of this type — start the flow again |
| 429 | Cooldown has not passed yet — try again after `resend_after` |

### Example

```bash
curl -X POST $API_URL/auth/resend-otp \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "otp_type": "registration_email"
  }'
```

**Cooldown response (429):**
```json
{
  "success": false,
  "status_code": 429,
  "message": "Please wait 45 seconds before requesting another code.",
  "error": { "code": "RATE_LIMIT_EXCEEDED" }
}
```

---

## POST /auth/login

Login with email or phone plus password. At least one of `email` or `phone`
is required.

If the contact method used has not been verified yet, the server auto-resends
the OTP (when the cooldown has passed) and returns **403 VERIFICATION_REQUIRED**.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | conditional | Required if no phone |
| `phone` | string | conditional | Required if no email |
| `password` | string | yes | |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "550e8400-...",
      "email": "john@example.com",
      "phone": null,
      "first_name": "John",
      "last_name": "Doe",
      "role": "customer"
    },
    "tokens": {
      "access": "eyJhbGci...",
      "refresh": "eyJhbGci...",
      "type": "Bearer",
      "expires_in": 1800
    }
  }
}
```

`expires_in` is in seconds. Access tokens expire in 30 minutes (1800 s);
refresh tokens expire in 30 days.

### Errors

| Status | Code | When |
|---|---|---|
| 401 | — | Wrong password — `message` includes remaining attempts |
| 403 | `VERIFICATION_REQUIRED` | Contact method not verified — OTP auto-sent |
| 403 | — | Account locked |

### Handling VERIFICATION_REQUIRED

```json
{
  "success": false,
  "status_code": 403,
  "message": "Email address not verified. A new verification code has been sent.",
  "error": {
    "code": "VERIFICATION_REQUIRED",
    "details": {
      "verification_required": true,
      "otp_type": "registration_email",
      "sent_to": "jo***@example.com"
    }
  }
}
```

The message changes depending on whether a new code was actually sent:
- `"A new verification code has been sent."` — code was resent
- `"Use the code already sent to your email."` — cooldown still active

Use `error.details.otp_type` and the `user_id` from a previous registration
response to call `POST /auth/resend-otp` manually if needed.

### Examples

```bash
# Login with email
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123"}'

# Login with phone
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "+12025550100", "password": "SecurePass123"}'
```

---

## POST /auth/refresh

Exchange a refresh token for a new access token. The refresh token itself
is not rotated — keep it secure and use it until it expires (30 days).

### Request

| Field | Type | Required |
|---|---|---|
| `refresh_token` | string | yes |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "Bearer",
    "expires_in": 1800
  }
}
```

### Errors

| Status | When |
|---|---|
| 401 | Refresh token is invalid, expired, or has been revoked |
| 403 | Account locked or unverified |

### Example

```bash
curl -X POST $API_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

---

## POST /auth/logout

Revoke a refresh token. The access token cannot be revoked directly —
it expires naturally after 30 minutes. Store the expiry client-side
and stop using it immediately on logout.

Requires a valid `Authorization` header (the access token).

### Request

| Field | Type | Required |
|---|---|---|
| `refresh_token` | string | yes |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Logged out successfully",
  "data": null
}
```

### Example

```bash
curl -X POST $API_URL/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

---

## POST /auth/register-master

Create the first master (system administrator) account. This is a
one-time bootstrap step — use the `MASTER_SECRET_KEY` configured in
your deployment secrets.

Master users are auto-verified and bypass all permission checks.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `secret_key` | string | yes | Must match `MASTER_SECRET_KEY` env var |
| `email` | string | yes | |
| `password` | string | yes | |
| `first_name` | string | yes | |
| `last_name` | string | yes | |
| `phone` | string | no | |

### Response `201`

```json
{
  "success": true,
  "status_code": 201,
  "message": "Master user created successfully",
  "data": {
    "user_id": "660f9511-...",
    "email": "admin@example.com",
    "role": "master",
    "email_verified": true,
    "phone_verified": false,
    "created_at": "2025-05-23T10:00:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| 403 | Wrong `secret_key` |
| 409 | Email already registered |
| 500 | `MASTER_SECRET_KEY` not configured |

### Example

```bash
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "YOUR_MASTER_SECRET_KEY",
    "email": "admin@yourcompany.com",
    "password": "SecurePass123!",
    "first_name": "System",
    "last_name": "Admin"
  }'
```
