# Profile Endpoints

---

## GET /auth/me

Get the current user's full profile.

**Auth:** Bearer token required.

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

## PUT /auth/me

Update the current user's profile. All fields are optional — send only
the fields you want to change.

**Auth:** Bearer token required.

### Direct updates (take effect immediately)

| Field | Type | Notes |
|---|---|---|
| `first_name` | string | |
| `last_name` | string | |
| `password` | string | Requires `current_password` in the same request |
| `current_password` | string | Required only when changing password |

### OTP-triggered updates (do not update the field directly)

| Field | Type | What happens |
|---|---|---|
| `email` | string | OTP sent to the **new** address. Email is updated only after `POST /auth/verify` with `otp_type: "add_email"` or `"change_email"` |
| `phone` | string | OTP sent to the **new** number. Phone is updated only after `POST /auth/verify` with `otp_type: "add_phone"` or `"change_phone"` |

The `otp_type` used depends on whether the field already exists on the account:

| Scenario | otp_type |
|---|---|
| Adding email for the first time | `add_email` |
| Changing existing email | `change_email` |
| Adding phone for the first time | `add_phone` |
| Changing existing phone | `change_phone` |

### Response `200`

**Name/password change (no OTP triggered):**
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
    ...
  }
}
```

**Email/phone change (OTP triggered):**
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
    ...
  }
}
```

The current email is **not changed yet**. After the user verifies the code,
the new email is applied to the account.

**Both direct and OTP-triggered in one request:**
```json
{
  "message": "Profile updated. Verification code sent to ***900.",
  "data": {
    "pending_verifications": [
      { "otp_type": "add_phone", "sent_to": "***900" }
    ],
    ...
  }
}
```

### Errors

| Status | When |
|---|---|
| 409 | New email or phone already in use by another account |
| 422 | Validation failed (field-level errors in `error.details`) |
| 400 | `current_password` wrong or no fields provided |

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
