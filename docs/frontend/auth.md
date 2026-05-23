# Authentication Endpoints

Core auth flows: register, verify OTP, resend OTP, login, refresh tokens, logout,
and the one-time master-user bootstrap.

---

## Contents

| Endpoint | Description |
|---|---|
| [`POST /auth/register`](#post-auth-register) | Create a new public account |
| [`POST /auth/verify`](#post-auth-verify) | Submit an OTP code |
| [`POST /auth/resend-otp`](#post-auth-resend-otp) | Resend a pending OTP |
| [`POST /auth/login`](#post-auth-login) | Login and receive tokens |
| [`POST /auth/refresh`](#post-auth-refresh) | Exchange refresh token for a new access token |
| [`POST /auth/logout`](#post-auth-logout) | Revoke a refresh token |
| [`POST /auth/register-master`](#post-auth-register-master) | Bootstrap the first master user |

---

<a id="post-auth-register"></a>

## `POST /auth/register`

```http
POST /auth/register
```

Register a new user. At least one of `email` or `phone` is required.
If `require_otp_on_registration` is enabled (default `true`), an OTP is sent
and the account cannot log in until that contact method is verified.

**Auth:** None  
**Prerequisites:** None

### Request Body

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | conditional | Required if no `phone` |
| `phone` | string | conditional | Required if no `email`. Formatting stripped automatically — `+12345678900` and `+1 (234) 567-8900` both work |
| `password` | string | yes | Min length set by `min_password_length` setting (default 4; use 8+ for production) |
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

Save the `user_id` — you'll need it for `POST /auth/verify` and `POST /auth/resend-otp`.

### Errors

| Status | When |
|---|---|
| `403` | Public signup disabled (`allow_public_signup = false`) |
| `409` | Email already registered |
| `409` | Phone already registered |
| `500` | OTP send failed — user record is rolled back so they can retry |

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

# Both email and phone
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

<a id="post-auth-verify"></a>

## `POST /auth/verify`

```http
POST /auth/verify
```

Submit a 6-digit OTP code. The `otp_type` tells the server what to do on
successful verification — mark email/phone verified, apply a pending contact change,
unlock a sensitive action, etc.

**Auth:** None  
**Prerequisites:** A pending OTP for this `user_id` + `otp_type` combination must exist. Created by `POST /auth/register`, `POST /auth/login` (VERIFICATION_REQUIRED flow), or `PUT /auth/me`

### Request Body

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
| `add_email` | Confirming a new email added via `PUT /auth/me` |
| `change_email` | Confirming a changed email via `PUT /auth/me` |
| `add_phone` | Confirming a new phone added via `PUT /auth/me` |
| `change_phone` | Confirming a changed phone via `PUT /auth/me` |
| `forgot_password` | Identity check before password reset *(endpoint coming)* |
| `login_otp` | Passwordless login *(future)* |
| `2fa` | Two-factor second step *(future)* |
| `sensitive_action` | Confirming high-risk action *(future)* |
| `device_verification` | New device check *(future)* |
| `delete_account` | Confirming account deletion *(future)* |
| `account_recovery` | Recovery flow *(future)* |

### Response `200`

The `data` shape depends on `otp_type`:

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
| `400` | Invalid or expired code |
| `404` | User not found |
| `409` | New email / phone is already taken by another account |

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

<a id="post-auth-resend-otp"></a>

## `POST /auth/resend-otp`

```http
POST /auth/resend-otp
```

Resend a pending OTP. The code is sent to the same contact address stored when
the OTP was first created — the caller cannot redirect it elsewhere.
A 60-second cooldown is enforced between resends.

**Auth:** None  
**Prerequisites:** A pending OTP of the specified type must already exist for this `user_id`. Created by `POST /auth/register`, the VERIFICATION_REQUIRED login flow, or `PUT /auth/me`

### Request Body

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
| `404` | User not found |
| `404` | No pending OTP of this type — start the flow again |
| `429` | Cooldown has not passed — retry after `resend_after` |

**Cooldown response (429):**
```json
{
  "success": false,
  "status_code": 429,
  "message": "Please wait 45 seconds before requesting another code.",
  "error": { "code": "RATE_LIMIT_EXCEEDED" }
}
```

### Example

```bash
curl -X POST $API_URL/auth/resend-otp \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "otp_type": "registration_email"
  }'
```

---

<a id="post-auth-login"></a>

## `POST /auth/login`

```http
POST /auth/login
```

Login with email or phone plus password. Returns an access token (30 min) and
a refresh token (30 days).

If the contact method used has not been verified yet, the server auto-resends the
OTP (when the cooldown has passed) and returns **403 VERIFICATION_REQUIRED**.

**Auth:** None  
**Prerequisites:** Account must exist. At least one contact method must be verified (unless `require_otp_on_registration = false`)

### Request Body

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | conditional | Required if no `phone` |
| `phone` | string | conditional | Required if no `email` |
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

`expires_in` is in seconds. Store both tokens client-side. Use `access` in the
`Authorization` header for protected requests. Use `refresh` to get a new access
token when it expires.

### Errors

| Status | Code | When |
|---|---|---|
| `401` | — | Wrong password — `message` includes remaining attempts before lock |
| `403` | `VERIFICATION_REQUIRED` | Contact method not verified — OTP auto-sent |
| `403` | — | Account locked |

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

The message differs depending on the OTP cooldown state:
- `"A new verification code has been sent."` — code was just resent
- `"Use the code already sent to your email."` — cooldown still active, use existing code

Use `error.details.otp_type` and the `user_id` from your registration response
to call `POST /auth/resend-otp` manually if needed.

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

<a id="post-auth-refresh"></a>

## `POST /auth/refresh`

```http
POST /auth/refresh
```

Exchange a refresh token for a new access token. The refresh token is **not
rotated** — keep it secure and reuse it until it expires (30 days).

**Auth:** None (refresh token in body)  
**Prerequisites:** A valid, non-revoked refresh token from a previous `POST /auth/login`

### Request Body

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
| `401` | Refresh token is invalid, expired, or has been revoked |
| `403` | Account locked or unverified |

### Example

```bash
curl -X POST $API_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

---

<a id="post-auth-logout"></a>

## `POST /auth/logout`

```http
POST /auth/logout
```

Revoke a refresh token. The access token cannot be revoked directly — it expires
naturally after 30 minutes. Discard it from client storage immediately on logout.

**Auth:** Bearer token (access token) required  
**Prerequisites:** A valid access token **and** the refresh token to revoke (both from `POST /auth/login`)

### Request Body

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

<a id="post-auth-register-master"></a>

## `POST /auth/register-master`

```http
POST /auth/register-master
```

Create the first master (system administrator) account. This is a one-time
bootstrap step — use the `MASTER_SECRET_KEY` configured in your deployment
secrets. Master users are auto-verified and bypass all permission checks.

**Auth:** Secret key in request body  
**Prerequisites:** `MASTER_SECRET_KEY` environment variable must be set on the server. Typically called once immediately after first deployment.

### Request Body

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
    "first_name": "System",
    "last_name": "Admin",
    "phone": null,
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
| `403` | Wrong `secret_key` |
| `409` | Email already registered |
| `500` | `MASTER_SECRET_KEY` not configured on the server |

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

---

> ← Previous: [Overview](overview.md) &nbsp;|&nbsp; Next → [Profile](profile.md)
