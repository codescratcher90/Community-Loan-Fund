# Frontend Integration Overview

Everything a frontend application needs to know before calling the API.

---

## Base URL

```
https://{api-id}.execute-api.{region}.amazonaws.com/{stage}
```

After deploying, the exact URL is shown in the GitHub Actions workflow summary,
or via: **AWS Console → CloudFormation → your stack → Outputs → ApiUrl**

---

## Response Envelope

Every response, success or error, uses the same shape:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Human-readable summary",
  "data": {},
  "error": null,
  "meta": {}
}
```

On errors, `success` is `false`, `data` is `null`, and `error` is populated:

```json
{
  "success": false,
  "status_code": 422,
  "message": "Validation failed",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": "Invalid email format",
      "password": "Minimum length is 8 characters"
    }
  },
  "meta": {}
}
```

---

## Authentication

Protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Access tokens expire in **30 minutes**. Use `POST /auth/refresh` with a refresh
token to get a new one. Refresh tokens expire in **30 days**.

---

## All Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Register with email, phone, or both |
| POST | `/auth/register-master` | Secret key in body | Bootstrap first master user |
| POST | `/auth/verify` | None | Submit OTP code |
| POST | `/auth/resend-otp` | None | Resend a pending OTP |
| POST | `/auth/login` | None | Login — returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token in body | Get new access token |
| POST | `/auth/logout` | Bearer token | Revoke refresh token |
| GET | `/auth/me` | Bearer token | Get own profile |
| PUT | `/auth/me` | Bearer token | Update profile |
| GET | `/users` | Bearer (owner+) | List users |
| POST | `/users` | Bearer (admin+) | Create internal user |
| GET | `/users/{id}` | Bearer (owner+) | Get user by ID |
| PUT | `/users/{id}/role` | Bearer (admin+) | Change user role |
| DELETE | `/users/{id}` | Bearer (master) | Delete user |
| GET | `/settings` | Bearer (owner+) | Get app settings |
| PUT | `/settings` | Bearer (master) | Update app settings |
| GET | `/permissions` | Bearer (master) | List all RBAC configs |
| GET | `/permissions/{resource}` | Bearer (master) | Get one resource's config |
| PUT | `/permissions/{resource}` | Bearer (master) | Replace a resource's config |
| POST | `/permissions/seed` | Bearer (master) | Write code defaults to DB |

---

## OTP Types

Every OTP has a `otp_type` that tells the verify endpoint what to do after
a successful code check.

| otp_type | Triggered by | What verify does |
|---|---|---|
| `registration_email` | Registration with email | Sets `email_verified = true` |
| `registration_phone` | Registration with phone | Sets `phone_verified = true` |
| `add_email` | PUT /auth/me adding first email | Applies new email to account |
| `change_email` | PUT /auth/me changing email | Applies new email to account |
| `add_phone` | PUT /auth/me adding first phone | Applies new phone to account |
| `change_phone` | PUT /auth/me changing phone | Applies new phone to account |
| `forgot_password` | *(future)* | Sets `password_reset_verified` flag (10 min) |
| `login_otp` | *(future)* passwordless login | Confirms identity |
| `2fa` | *(future)* two-factor auth | Confirms second factor |
| `sensitive_action` | *(future)* high-risk action | Confirms intent |
| `device_verification` | *(future)* new device | Confirms new device |
| `delete_account` | *(future)* account deletion | Confirms deletion |
| `account_recovery` | *(future)* recovery flow | Confirms identity |

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (invalid input) |
| 401 | Missing or invalid token |
| 403 | Authenticated but not authorized (or account locked/unverified) |
| 404 | Resource not found |
| 409 | Conflict (e.g. email already registered) |
| 422 | Validation error — `error.details` has field-level messages |
| 429 | Rate limit exceeded or OTP cooldown in effect |
| 500 | Server error |

---

## Error Codes

| `error.code` | When it appears |
|---|---|
| `UNAUTHORIZED` | Missing/invalid/expired token |
| `FORBIDDEN` | Valid token but insufficient permissions |
| `VERIFICATION_REQUIRED` | Login attempted with unverified contact method |
| `VALIDATION_ERROR` | Request body failed field validation |
| `INVALID_JSON` | Request body is not valid JSON |
| `RATE_LIMIT_EXCEEDED` | Too many requests from this IP or user |
| `NOT_FOUND` | Resource does not exist |
| `ROUTE_NOT_FOUND` | No handler for this method + path |
| `INTERNAL_SERVER_ERROR` | Unhandled server error |

---

## Verification Flow (Registration)

```
1. POST /auth/register          → user created, OTP sent
2.   ↳ email OTP sent           → user receives 6-digit code in email
3.   ↳ SMS OTP sent (optional)  → user receives 6-digit code via SMS
4. POST /auth/verify            → submit code with otp_type
5. POST /auth/login             → now allowed
```

If the user doesn't receive the code:
```
POST /auth/resend-otp  →  new code sent (60 s cooldown between resends)
```

---

## Profile Contact Change Flow

Changing email or phone via `PUT /auth/me` does **not** update the field
immediately. It triggers a verification flow:

```
1. PUT /auth/me  { "email": "new@example.com" }
   → OTP sent to new@example.com
   → response includes pending_verifications

2. POST /auth/verify  { "user_id": "...", "code": "123456", "otp_type": "change_email" }
   → email updated on account
```

---

## See Also

- [Authentication endpoints](auth.md) — register, verify, login, refresh, logout
- [Profile endpoints](profile.md) — GET/PUT /auth/me
- [User management](users.md) — /users
- [Settings](settings.md) — /settings
- [Permissions](permissions.md) — /permissions
