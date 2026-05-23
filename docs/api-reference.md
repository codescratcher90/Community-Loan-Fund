# API Reference

All responses share this envelope:

```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": {},
  "error": null,
  "meta": {}
}
```

---

## Endpoints

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Public user registration |
| POST | `/auth/register-master` | Secret key in body | Create master user |
| POST | `/auth/verify` | None | Submit OTP code |
| POST | `/auth/resend-otp` | None | Resend a pending OTP |
| POST | `/auth/login` | None | Login — returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token in body | Get new access token |
| POST | `/auth/logout` | Bearer token | Revoke refresh token |
| GET | `/auth/me` | Bearer token | Get own profile |
| PUT | `/auth/me` | Bearer token | Update own profile |

### User Management

| Method | Path | Default Min Role | Tenant Scope |
|---|---|---|---|
| GET | `/users` | supervisor | master: all users · internal: own tenant |
| POST | `/users` | admin | master: any tenant · internal: own tenant |
| GET | `/users/{id}` | supervisor | master: any · internal: own tenant |
| PUT | `/users/{id}/role` | admin | master: any · internal: own tenant |
| DELETE | `/users/{id}` | master | master only |

Min roles are the seeded defaults. Master can change them at runtime via `PUT /permissions/users`.

### Settings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/settings` | Bearer (owner+) | Get all app settings |
| PUT | `/settings` | Bearer (master) | Update app settings (partial) |

### Permissions

All permission endpoints require a master token.
Default roles shown are the seeded values and can be changed at runtime.

| Method | Path | Description |
|---|---|---|
| GET | `/permissions` | List all resource configs + seed template |
| GET | `/permissions/{resource}` | Get one resource's operation→role map |
| PUT | `/permissions/{resource}` | Full replace of a resource's config |
| POST | `/permissions/seed` | Write code defaults to DynamoDB (idempotent) |

---

## Request & Response Examples

<details>
<summary><b>POST /auth/register</b></summary>

At least one of `email` or `phone` must be provided — you do not need both. `password`, `first_name`, and `last_name` are always required.

Email and phone are masked in the response. `is_verified` is `false` when the `require_otp_on_registration` setting is enabled (the default).

**Email-only registration**
```bash
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Verification code sent via email (us***@example.com).",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "us***@example.com",
    "phone": null,
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "email_verified": false,
    "phone_verified": false,
    "is_verified": false,
    "created_at": "2025-05-23T10:30:00.000000"
  }
}
```

**Phone-only registration**
```bash
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Verification code sent via SMS (***890).",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": null,
    "phone": "***890",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "email_verified": false,
    "phone_verified": false,
    "is_verified": false,
    "created_at": "2025-05-23T10:30:00.000000"
  }
}
```

**Email + phone registration**
```bash
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "phone": "+1234567890",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Verification code sent via email (us***@example.com).",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "us***@example.com",
    "phone": "***890",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "email_verified": false,
    "phone_verified": false,
    "is_verified": false,
    "created_at": "2025-05-23T10:30:00.000000"
  }
}
```
</details>

<details>
<summary><b>POST /auth/register-master</b></summary>

```bash
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "YOUR_MASTER_SECRET_KEY",
    "email": "admin@example.com",
    "password": "SecurePass123",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Master user created successfully",
  "data": {
    "user_id": "660f9511-...",
    "email": "admin@example.com",
    "role": "master",
    "is_verified": true
  }
}
```
</details>

<details>
<summary><b>POST /auth/verify</b></summary>

`otp_type` must be one of: `registration_email`, `registration_phone`, `login_otp`, `2fa`, `forgot_password`, `account_recovery`, `add_email`, `add_phone`, `change_email`, `change_phone`, `sensitive_action`, `device_verification`, `delete_account`.

Response `data` varies by `otp_type`:
- `registration_email` / `registration_phone` → `user_id`, `otp_type`, `email_verified`, `phone_verified` (if applicable), `is_verified`
- `add_email` / `change_email` → `user_id`, `otp_type`, `email` (masked), `email_verified: true`, `is_verified`
- `add_phone` / `change_phone` → `user_id`, `otp_type`, `phone` (masked), `phone_verified: true`, `is_verified`
- `forgot_password` → `user_id`, `otp_type`, `password_reset_expires_at` (ISO timestamp)
- All other types → `user_id`, `otp_type`

**Example — registration_email**
```bash
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "123456",
    "otp_type": "registration_email"
  }'
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Email verified successfully",
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "registration_email",
    "email_verified": true,
    "phone_verified": false,
    "is_verified": true
  }
}
```

**Example — change_email**
```bash
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "654321",
    "otp_type": "change_email"
  }'
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Email updated successfully",
  "data": {
    "user_id": "550e8400-...",
    "otp_type": "change_email",
    "email": "ne***@newdomain.com",
    "email_verified": true,
    "is_verified": true
  }
}
```
</details>

<details>
<summary><b>POST /auth/resend-otp</b></summary>

Resends a pending OTP for the given user and `otp_type`. No authentication required.

```bash
curl -X POST $API_URL/auth/resend-otp \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "otp_type": "registration_email"
  }'
```

```json
{
  "success": true,
  "message": "Verification code resent",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "otp_type": "registration_email",
    "sent_to": "us***@example.com",
    "resend_after": "2025-05-23T10:31:00.000000"
  }
}
```

**429 — cooldown has not passed**
```json
{
  "success": false,
  "status_code": 429,
  "message": "Please wait 45 seconds before requesting another code."
}
```
</details>

<details>
<summary><b>POST /auth/login</b></summary>

Accepts `email` or `phone` (at least one required) plus `password`. If the contact used to log in is unverified, a `403 VERIFICATION_REQUIRED` error is returned and a new OTP is automatically sent (if the cooldown has passed).

**Login with email**
```bash
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

**Login with phone**
```bash
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "password": "SecurePass123"}'
```

**200 — success**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "550e8400-...",
      "email": "user@example.com",
      "first_name": "John",
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

Access token expires in 30 min (1800 s). Refresh token expires in 30 days.

**403 — contact not verified**
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
      "sent_to": "us***@example.com"
    }
  }
}
```
</details>

<details>
<summary><b>POST /auth/refresh</b></summary>

```bash
curl -X POST $API_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

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
</details>

<details>
<summary><b>POST /auth/logout</b></summary>

```bash
curl -X POST $API_URL/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

```json
{"success": true, "status_code": 200, "message": "Logged out successfully", "data": null}
```
</details>

<details>
<summary><b>GET /auth/me</b></summary>

```bash
curl -X GET $API_URL/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "user_id": "550e8400-...",
    "email": "user@example.com",
    "phone": null,
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "email_verified": true,
    "phone_verified": false,
    "is_verified": true,
    "is_locked": false,
    "created_at": "2025-05-23T10:30:00.000000",
    "updated_at": "2025-05-23T10:30:00.000000"
  }
}
```

`email` and `phone` may be `null` if the user has not provided them.
</details>

<details>
<summary><b>PUT /auth/me — update profile</b></summary>

Name and password changes apply immediately. When `email` or `phone` is included in the body, the value is **not** updated directly — instead an OTP is sent to the new address/number and `pending_verifications` is returned in the response. The change takes effect once the OTP is verified.

```bash
# Update name only (applies immediately)
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Johnny"}'

# Change password (applies immediately — requires current_password)
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "SecurePass123", "password": "NewSecurePass456"}'
```

Changing password requires `current_password`.

**Email change request — OTP sent, not applied yet**
```bash
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newemail@example.com"}'
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Verification code sent to ne***@example.com. Verify to complete the change.",
  "data": {
    "pending_verifications": ["change_email"]
  }
}
```

Once the user submits the OTP via `POST /auth/verify` with `otp_type: "change_email"`, the email is updated and `email_verified` is set to `true`. The same flow applies to phone changes (`change_phone` / `add_phone`).
</details>

<details>
<summary><b>GET /users — list users</b></summary>

```bash
curl -X GET "$API_URL/users?limit=100" -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "users": [
      {
        "user_id": "550e8400-...",
        "email": "staff@hotel.com",
        "role": "staff",
        "tenant_id": "hotel-abc-123",
        "is_verified": true,
        "is_locked": false,
        "created_at": "2025-05-23T11:00:00.000000"
      }
    ],
    "count": 1
  }
}
```

Master sees all users. Internal roles see only their tenant's users.
</details>

<details>
<summary><b>POST /users — create internal user</b></summary>

```bash
# Master creates an owner for a new tenant
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@hotel.com",
    "password": "SecurePass123",
    "first_name": "Hotel",
    "last_name": "Owner",
    "role": "owner",
    "tenant_id": "hotel-abc-123"
  }'

# Admin creates staff in their own tenant (no tenant_id needed)
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "staff@hotel.com",
    "password": "Staff123",
    "first_name": "Alice",
    "last_name": "Smith",
    "role": "staff"
  }'
```

Internal users are auto-verified (no OTP needed). Admin+ cannot create owners.
</details>

<details>
<summary><b>PUT /users/{id}/role</b></summary>

```bash
curl -X PUT $API_URL/users/550e8400-.../role \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

Rules:
- Cannot promote to your own level or above
- Cannot change the role of a peer or superior
- Cannot assign or remove the `master` role (master only modifies others, not itself)
</details>

<details>
<summary><b>DELETE /users/{id}</b></summary>

```bash
curl -X DELETE $API_URL/users/550e8400-... -H "Authorization: Bearer $MASTER_TOKEN"
```

Master only. Cannot delete your own account. Also deletes all refresh tokens for the user.
</details>

<details>
<summary><b>GET /settings</b></summary>

```bash
curl -X GET $API_URL/settings -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {
    "allow_public_signup": true,
    "allow_adding_new_users": true,
    "require_otp_on_registration": true,
    "email_verification_required": true,
    "default_public_role": "customer",
    "min_password_length": 4,
    "max_failed_login_attempts": 5,
    "account_lockout_duration_minutes": 30
  }
}
```
</details>

<details>
<summary><b>PUT /settings</b></summary>

```bash
curl -X PUT $API_URL/settings \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_password_length": 12,
    "max_failed_login_attempts": 3,
    "account_lockout_duration_minutes": 60
  }'
```

Partial updates only — omit fields you don't want to change.
</details>

<details>
<summary><b>GET /permissions</b></summary>

```bash
curl -X GET $API_URL/permissions -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {
    "resources": {
      "users": {
        "operations": {
          "list":        ["owner", "admin", "manager", "supervisor"],
          "read":        ["owner", "admin", "manager", "supervisor"],
          "create":      ["owner", "admin"],
          "update_role": ["owner", "admin"],
          "delete":      []
        },
        "created_at": "2025-05-23T10:00:00.000000",
        "updated_at": "2025-05-23T10:00:00.000000"
      },
      "settings": {
        "operations": {
          "read":   ["owner"],
          "update": []
        },
        "created_at": "2025-05-23T10:00:00.000000",
        "updated_at": "2025-05-23T10:00:00.000000"
      }
    },
    "default_config": { "...": "code defaults for reference" }
  }
}
```

`resources` reflects what is currently stored in DynamoDB. `default_config` is the hard-coded seed template.
Empty list `[]` means master-only.
</details>

<details>
<summary><b>GET /permissions/{resource}</b></summary>

```bash
curl -X GET $API_URL/permissions/users -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {
    "resource": "users",
    "operations": {
      "list":        ["owner", "admin", "manager", "supervisor"],
      "read":        ["owner", "admin", "manager", "supervisor"],
      "create":      ["owner", "admin"],
      "update_role": ["owner", "admin"],
      "delete":      []
    },
    "display_name": "User Management",
    "description": "Manage tenant users",
    "created_at": "2025-05-23T10:00:00.000000",
    "updated_at": "2025-05-23T10:00:00.000000"
  }
}
```

Returns 404 if no config exists for the resource — call `POST /permissions/seed` first.
</details>

<details>
<summary><b>PUT /permissions/{resource}</b></summary>

Full replace of a resource's operation config. Cache is auto-cleared on update so the change takes effect immediately on the current Lambda container.

`display_name` and `description` are optional — if omitted they are preserved from the existing record.

```bash
# Give coordinator and staff read access to users
curl -X PUT $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operations": {
      "list":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
      "read":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
      "create":      ["owner", "admin"],
      "update_role": ["owner", "admin"],
      "delete":      []
    },
    "display_name": "User Management",
    "description":  "Manage tenant users"
  }'
```

```json
{
  "data": {
    "resource": "users",
    "operations": {
      "list":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
      "read":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
      "create":      ["owner", "admin"],
      "update_role": ["owner", "admin"],
      "delete":      []
    },
    "display_name": "User Management",
    "description":  "Manage tenant users",
    "created_at": "2025-05-23T10:00:00.000000",
    "updated_at": "2025-05-23T12:00:00.000000"
  },
  "message": "Permissions updated for resource 'users'"
}
```

Rules:
- `master` always has access and must **not** be listed in any role array
- Empty array `[]` = master-only access
- You cannot partially update — always send the full `operations` map
</details>

<details>
<summary><b>POST /permissions/seed</b></summary>

Writes the hard-coded `DEFAULT_RESOURCE_PERMISSIONS` from `config/permissions.py` to DynamoDB. Safe to call multiple times (idempotent). Call this after a fresh deploy or after adding a new resource to code defaults.

```bash
curl -X POST $API_URL/permissions/seed -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {"seeded": ["users", "settings", "permissions"]},
  "message": "Seeded permissions for 3 resources"
}
```
</details>

---

## Error Responses

### 401 Unauthorized
```json
{
  "success": false,
  "status_code": 401,
  "message": "Invalid or expired token",
  "error": {"code": "UNAUTHORIZED"}
}
```

### 403 Forbidden
```json
{
  "success": false,
  "status_code": 403,
  "message": "You do not have permission to perform this action",
  "error": {"code": "FORBIDDEN"}
}
```

### 403 Verification Required

Returned by `POST /auth/login` when the contact used to log in has not yet been verified. A new OTP is automatically sent if the cooldown has passed.

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
      "sent_to": "us***@example.com"
    }
  }
}
```

Use `POST /auth/resend-otp` to request a new code if the cooldown has not yet passed.

### 422 Validation Error
```json
{
  "success": false,
  "status_code": 422,
  "message": "Validation failed",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": "Invalid email format",
      "password": "Password must be at least 8 characters"
    }
  }
}
```

### 429 Rate Limit
```json
{
  "success": false,
  "status_code": 429,
  "message": "Rate limit exceeded - Too many requests",
  "error": {"code": "RATE_LIMIT_EXCEEDED"}
}
```
