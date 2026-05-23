# Architecture

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 on AWS Lambda |
| API | AWS API Gateway (REST) |
| Database | AWS DynamoDB (6 tables, PAY_PER_REQUEST) |
| Auth | JWT (PyJWT) + bcrypt |
| IaC | AWS SAM (`template.yaml`) |
| CI/CD | GitHub Actions |

---

## System Diagram

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  API Client │─────▶│ API Gateway  │─────▶│   Lambda    │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                               DynamoDB        DynamoDB        DynamoDB
                                Users          Tokens          Settings
```

## Request Flow

```
API Gateway
  └─ lambda_handler()
       ├─ OPTIONS → 200 CORS preflight (immediate)
       ├─ match_route(method, path) → find handler
       └─ middleware stack (outermost → innermost):
            rate_limit → require_auth → validate_request_body → handler
                                                                    └─ success_response / error_response
```

All responses share a standard envelope:
```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": { "..." },
  "error": null,
  "meta": {}
}
```

---

## Project Structure

```
Basic-Auth/
├── lambda_function.py         # Entry point — routes requests to handlers
├── template.yaml              # SAM infrastructure (Lambda + API GW + DynamoDB)
├── requirements.txt           # boto3, PyJWT, bcrypt, python-dotenv
│
├── config/
│   ├── settings.py            # Config class — reads env vars
│   ├── otp.py                 # OTPType constants, EMAIL/PHONE_OTP_TYPES, cooldown
│   └── permissions.py        # Role hierarchy + DEFAULT_RESOURCE_PERMISSIONS
│
├── handlers/                  # One file per feature area
│   ├── register.py            # POST /auth/register, POST /auth/register-master
│   ├── login.py               # POST /auth/login
│   ├── logout.py              # POST /auth/logout
│   ├── refresh_token.py       # POST /auth/refresh
│   ├── verify.py              # POST /auth/verify, POST /auth/resend-otp
│   ├── profile.py             # GET/PUT /auth/me
│   ├── users.py               # GET/POST/PUT/DELETE /users and /users/{id}
│   └── settings.py            # GET/PUT /settings
│
├── middleware/
│   ├── auth.py                # @require_auth decorator (JWT validation + RBAC)
│   └── rate_limiting.py       # Per-IP and per-user rate limit decorators
│
├── utils/
│   ├── database.py            # DynamoDB wrappers: UserDB, RefreshTokenDB, etc.
│   ├── jwt_utils.py           # Token creation and validation
│   ├── password.py            # bcrypt hash/verify
│   ├── verification.py        # OTP generation + send (SES/SNS stubs)
│   ├── responses.py           # success_response / error_response helpers
│   ├── validators.py          # Email, phone, password, name validators
│   ├── schemas.py             # Request body schema definitions
│   ├── schema_validator.py    # SchemaField, Schema, @validate_request_body
│   └── app_settings.py        # Runtime settings + resource permissions from DynamoDB
│
└── docs/                      # Project documentation
    ├── api-reference.md
    ├── architecture.md        # ← you are here
    ├── deployment.md
    ├── examples.md
    └── next-steps.md
```

---

## Role Hierarchy

The system has an **8-tier role hierarchy**. A higher number means more privileges.

| Role | Level | Category | Description |
|---|---|---|---|
| master | 8 | System | Cross-tenant god mode — the operator |
| owner | 7 | Internal | Tenant owner — full control of their org |
| admin | 6 | Internal | Tenant administrator |
| manager | 5 | Internal | Tenant manager |
| supervisor | 4 | Internal | Tenant supervisor |
| coordinator | 3 | Internal | Tenant coordinator |
| staff | 2 | Internal | Tenant staff member |
| customer | 1 | External | Global user — no tenant |

**Internal roles** (`owner` → `staff`) are scoped to a `tenant_id`.
**External roles** (`customer`) exist globally — no tenant, can interact with multiple orgs.
**System roles** (`master`) have no tenant, full cross-tenant access.

### Role Mapping Examples

Because the roles are generic, map them to whatever job titles fit your use case:

| Generic | Hotel | Restaurant | Gym | SaaS |
|---|---|---|---|---|
| owner | Hotel Owner | Chain Owner | Gym Owner | Company Admin |
| admin | General Manager | Regional Manager | Gym Manager | Team Lead |
| manager | Dept. Manager | Location Manager | Head Trainer | Project Manager |
| supervisor | Shift Supervisor | Shift Lead | Senior Trainer | Senior Dev |
| coordinator | Guest Relations | Event Coordinator | Class Coordinator | Coordinator |
| staff | Receptionist | Server / Chef | Trainer | Team Member |
| customer | Hotel Guest | Diner | Gym Member | End User |

---

## Permissions System

### Model: Resource + Operation (secure by default)

Every protected endpoint declares a **resource** and an **operation**:

```python
@require_auth(resource='users', operation='list')
def list_users(event, context): ...
```

At request time, `has_resource_permission(resource, operation, role)` checks the
`app_settings` DynamoDB table for a record keyed `resource_permission:{resource}`.
The record is a JSON object mapping operation names to lists of allowed roles.

**Secure by default**: if no DB record exists for a resource, or the operation key
is absent from the record, access is **denied** for everyone except `master`.
`master` always bypasses all permission checks.

### Default Permission Matrix (seed values)

Stored in `config/permissions.py → DEFAULT_RESOURCE_PERMISSIONS`. Written to DynamoDB
by calling `POST /permissions/seed` (master only, idempotent).

| Resource | Operation | owner | admin | manager | supervisor | staff | customer |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| users | list | ✓ | ✓ | ✓ | ✓ | | |
| users | read | ✓ | ✓ | ✓ | ✓ | | |
| users | create | ✓ | ✓ | | | | |
| users | update_role | ✓ | ✓ | | | | |
| users | delete | — | — | — | — | — | — |
| settings | read | ✓ | | | | | |
| settings | update | — | — | — | — | — | — |
| permissions | read | ✓ | | | | | |
| permissions | update | — | — | — | — | — | — |

`—` means master-only (empty list `[]` or operation absent from config).
`master` always has access and cannot be listed in any permission config.

### Runtime Permission Changes

The master can change which roles access any resource/operation without redeploying:

```bash
# View all resource permission configs
curl -X GET $API_URL/permissions \
  -H "Authorization: Bearer $MASTER_TOKEN"

# View permissions for one resource
curl -X GET $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN"

# Full replace of a resource's operations
# coordinator and staff can now list and read users; delete is still master-only
curl -X PUT $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "list":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
    "read":        ["owner", "admin", "manager", "supervisor", "coordinator", "staff"],
    "create":      ["owner", "admin"],
    "update_role": ["owner", "admin"],
    "delete":      []
  }'
```

Permissions are stored in `app_settings` under keys like `resource_permission:users`.
Changes via the API take effect immediately (write-through cache). Manual DynamoDB edits propagate within 60 seconds (TTL-based cache).

### Adding a New Endpoint (for developers)

1. Write the handler function in the appropriate `handlers/` file
2. Apply `@require_auth(resource='<resource>', operation='<operation>')` to it
3. Wire the route in `lambda_function.py → ROUTES`
4. Add the API Gateway event + swagger path in `template.yaml`
5. Add the new resource/operation to `DEFAULT_RESOURCE_PERMISSIONS` in `config/permissions.py`
6. After deploying, call `POST /permissions/seed` to write the new defaults to DynamoDB

See `CLAUDE.md` for the full checklist.

---

## Multi-Tenant Model

```
┌───────────────────────────────────────────┐
│  SYSTEM LEVEL                             │
│  master — full access to all tenants      │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│  TENANT LEVEL  (scoped to one org)        │
│  owner → admin → manager → supervisor    │
│       → coordinator → staff              │
│                                           │
│  Each user has tenant_id.                 │
│  Can only access resources in their org.  │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│  GLOBAL LEVEL  (no tenant)                │
│  customer — external user, no tenant_id   │
│  Can interact with multiple orgs.         │
│  Sees only their own resources.           │
└───────────────────────────────────────────┘
```

**Tenant isolation** is enforced by `check_tenant_access()` in `config/permissions.py`:
- `master` → any resource in any tenant
- Internal roles → only resources where `tenant_id` matches their own
- `customer` → only resources where they are the `resource_owner_id`

---

## DynamoDB Tables

All tables are named `{APP_NAME}-{ENVIRONMENT}-{table}` (e.g. `community-fund-prod-users`).

| Table | Primary Key | GSI | TTL |
|---|---|---|---|
| users | `user_id` (HASH) | `email-index, phone-index (sparse)` | No |
| refresh_tokens | `token` (HASH) | `user_id-index` | Yes (`expires_at`) |
| verification_codes | `user_id` (HASH) + `code_type` (RANGE) | — | No (bug — see next-steps §1.5) |
| login_attempts | `ip_address` (HASH) + `timestamp` (RANGE) | — | No (bug — see next-steps §1.6) |
| rate_limits | `limit_key` (HASH) | — | No |
| app_settings | `setting_key` (HASH) | — | No |

The `app_settings` table stores both general settings (e.g. `allow_public_signup`) and resource
permission configs (e.g. `resource_permission:users → {"list":["owner","admin",...], ...}`).

---

## Environment Variables

Set automatically by SAM from `template.yaml`. For local dev create `.env`:

```env
APP_NAME=basic-auth
ENVIRONMENT=dev
JWT_SECRET=<openssl rand -base64 32>
REFRESH_TOKEN_SECRET=<openssl rand -base64 32>
MASTER_SECRET_KEY=<openssl rand -base64 32>
AWS_REGION=eu-north-1
FROM_EMAIL=noreply@yourdomain.com
```

Do **not** commit `.env` — it is in `.gitignore`.

---

## Security Notes

- **Secrets**: Use `openssl rand -base64 32` to generate JWT and master secrets
- **CORS**: `Access-Control-Allow-Origin: *` is fine for development; restrict to your frontend domain in production (see `next-steps.md §2.3`)
- **HTTPS**: API Gateway enforces HTTPS by default — no action needed
- **Bcrypt**: All passwords are hashed with bcrypt; cost factor is configurable
- **Rate limiting**: Per-IP and per-user limits are applied via middleware decorators
- **Account locking**: Configurable max failed login attempts and lockout duration via `/settings`
