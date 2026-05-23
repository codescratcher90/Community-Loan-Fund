# Settings Endpoints

Read and update application-wide configuration. Settings affect registration
behaviour, password policy, and account lockout. Changes take effect within
60 seconds across all Lambda containers.

---

## Contents

| Endpoint | Description |
|---|---|
| [`GET /settings`](#get-settings) | Read all current settings |
| [`PUT /settings`](#put-settings) | Update one or more settings |

---

<a id="get-settings"></a>

## `GET /settings`

```http
GET /settings
```

Get all application settings.

**Auth:** Bearer token required. Role: owner or above  
**Prerequisites:** A valid access token from `POST /auth/login` with owner or higher role

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "allow_public_signup": true,
    "allow_adding_new_users": true,
    "require_otp_on_registration": true,
    "default_public_role": "customer",
    "min_password_length": 4,
    "max_failed_login_attempts": 5,
    "account_lockout_duration_minutes": 30
  }
}
```

### Settings Reference

| Key | Type | Default | Description |
|---|---|---|---|
| `allow_public_signup` | boolean | `true` | Whether `POST /auth/register` is open to the public. Set to `false` to disable self-registration. |
| `allow_adding_new_users` | boolean | `true` | Whether `POST /users` can be used to create internal users. |
| `require_otp_on_registration` | boolean | `true` | When `true`: OTP is sent at registration and login is blocked until the contact method is verified. When `false`: users are auto-verified and can log in immediately. |
| `default_public_role` | string | `"customer"` | Role assigned to users who register via `POST /auth/register`. |
| `min_password_length` | integer | `4` | Minimum password length (4–128). Raise to 8+ for production. |
| `max_failed_login_attempts` | integer | `5` | Failed logins before account is locked (1–100). |
| `account_lockout_duration_minutes` | integer | `30` | How long an account stays locked (0–10080). `0` = permanent lock until manually unlocked. |

### Example

```bash
curl -X GET $API_URL/settings \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

<a id="put-settings"></a>

## `PUT /settings`

```http
PUT /settings
```

Update one or more application settings. Only the fields you send are changed —
this is a partial update. Changes propagate to all Lambda containers within 60 s.

**Auth:** Bearer token required. Role: **master only**  
**Prerequisites:** A valid master access token from `POST /auth/login`

### Request Body

Send any subset of the writable settings:

```json
{
  "min_password_length": 8,
  "max_failed_login_attempts": 3
}
```

### Validation Rules

| Key | Constraint |
|---|---|
| `min_password_length` | Integer between `4` and `128` |
| `max_failed_login_attempts` | Integer between `1` and `100` |
| `account_lockout_duration_minutes` | Integer between `0` and `10080` |
| `default_public_role` | One of: `master`, `owner`, `admin`, `manager`, `supervisor`, `coordinator`, `staff`, `customer` |
| `allow_public_signup` | Boolean |
| `allow_adding_new_users` | Boolean |
| `require_otp_on_registration` | Boolean |

### Response `200`

Returns only the keys that were updated:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Successfully updated 2 setting(s)",
  "data": {
    "min_password_length": 8,
    "max_failed_login_attempts": 3
  }
}
```

### Errors

| Status | When |
|---|---|
| `403` | Insufficient role |
| `422` | Unknown key, wrong type, or value out of range |

### Examples

```bash
# Require stronger passwords
curl -X PUT $API_URL/settings \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"min_password_length": 12}'

# Disable public self-registration
curl -X PUT $API_URL/settings \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"allow_public_signup": false}'

# Skip OTP at registration (dev / test only)
curl -X PUT $API_URL/settings \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"require_otp_on_registration": false}'
```

---

> ← Previous: [Users](users.md) &nbsp;|&nbsp; Next → [Permissions](permissions.md)
