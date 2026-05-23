# Profile Endpoints

Read and update the currently authenticated user's own profile. Email and phone
changes go through an OTP verification step rather than updating immediately.

---

## Contents

| # | Endpoint | Description |
|---|---|---|
| 1 | [GET /auth/me](#get-auth-me) | Get the current user's full profile |
| 2 | [PUT /auth/me](#put-auth-me) | Update name, password, email, or phone |

---

<a id="get-auth-me"></a>

## 1. GET /auth/me

```http
GET /auth/me
```

Get the current user's full profile.

**Auth:** Bearer token required  
**Prerequisites:** A valid access token from `POST /auth/login`

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "phone": "+12025550100",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "tenant_id": null,
    "email_verified": true,
    "phone_verified": false,
    "is_locked": false,
    "created_at": "2025-05-23T10:30:00.000000",
    "updated_at": "2025-05-23T11:00:00.000000"
  }
}
```

`email` and `phone` are `null` if the user has not provided them.  
`tenant_id` is `null` for `customer` role users and the `master` role.

### Example

```bash
curl -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

<a id="put-auth-me"></a>

## 2. PUT /auth/me

```http
PUT /auth/me
```

Update the current user's profile. All fields are optional — send only the
fields you want to change. Some fields take effect immediately; others trigger
an OTP flow and are applied only after verification.

**Auth:** Bearer token required  
**Prerequisites:** A valid access token from `POST /auth/login`

### Direct Updates (take effect immediately)

| Field | Type | Notes |
|---|---|---|
| `first_name` | string | |
| `last_name` | string | |
| `password` | string | Requires `current_password` in the same request |
| `current_password` | string | Required only when changing password |

### OTP-Triggered Updates (do not update the field directly)

| Field | Type | What happens |
|---|---|---|
| `email` | string | OTP sent to the **new** address. Email is updated only after `POST /auth/verify` with the correct `otp_type` |
| `phone` | string | OTP sent to the **new** number. Phone is updated only after `POST /auth/verify` with the correct `otp_type` |

The `otp_type` used depends on whether the field already exists on the account:

| Scenario | `otp_type` |
|---|---|
| Adding email for the first time | `add_email` |
| Changing an existing email | `change_email` |
| Adding phone for the first time | `add_phone` |
| Changing an existing phone | `change_phone` |

### Response `200`

**Name / password change (no OTP triggered):**
```json
{
  "success": true,
  "message": "Profile updated.",
  "data": {
    "user_id": "550e8400-...",
    "email": "john@example.com",
    "phone": null,
    "first_name": "Johnny",
    "last_name": "Doe",
    "email_verified": true,
    "phone_verified": false,
    "..."
  }
}
```

**Email / phone change (OTP triggered):**
```json
{
  "success": true,
  "message": "Verification code sent to ne***@example.com.",
  "data": {
    "user_id": "550e8400-...",
    "email": "john@example.com",
    "phone": null,
    "first_name": "John",
    "last_name": "Doe",
    "email_verified": true,
    "phone_verified": false,
    "pending_verifications": [
      {
        "otp_type": "change_email",
        "sent_to": "ne***@example.com"
      }
    ],
    "..."
  }
}
```

The current email is **not changed yet**. The new email is applied only after
the user verifies the code via `POST /auth/verify`.

**Both direct and OTP-triggered in one request:**
```json
{
  "message": "Profile updated. Verification code sent to ***900.",
  "data": {
    "pending_verifications": [
      { "otp_type": "add_phone", "sent_to": "***900" }
    ],
    "..."
  }
}
```

### Errors

| Status | When |
|---|---|
| `400` | `current_password` wrong, or no fields provided |
| `409` | New email or phone already in use by another account |
| `422` | Validation failed (field-level errors in `error.details`) |

### Examples

```bash
# Change name
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Johnny"}'

# Change password
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPass123",
    "password": "NewPass456"
  }'

# Request email change (OTP sent to new address)
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "new.email@example.com"}'

# Complete email change (after receiving OTP)
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "482951",
    "otp_type": "change_email"
  }'
```

---

## Related

- [Authentication](auth.md) — where access tokens come from (login, refresh)
- [Users](users.md) — admin-level user management
