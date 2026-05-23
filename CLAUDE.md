# CLAUDE.md — Basic-Auth Project

## What This Is

A serverless authentication API built on AWS Lambda + API Gateway + DynamoDB.
It handles registration, login, JWT access/refresh tokens, email/SMS verification,
account locking, rate limiting, and multi-tenant user management.

Designed to be white-label and reusable: deploy multiple isolated instances in
the same AWS account by changing `APP_NAME` (e.g. `hotel-manager`, `community-fund`).

---

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 on AWS Lambda |
| API | AWS API Gateway (REST) |
| Database | AWS DynamoDB (6 tables, PAY_PER_REQUEST) |
| Auth | JWT (PyJWT) + bcrypt |
| IaC | AWS SAM (template.yaml) |
| CI/CD | GitHub Actions |

---

## Project Structure

```
Basic-Auth/
├── lambda_function.py        # Entry point — routes requests to handlers
├── template.yaml             # SAM infrastructure definition (Lambda + API GW + DynamoDB)
├── requirements.txt          # Python deps: boto3, PyJWT, bcrypt, python-dotenv
├── init_settings.py          # One-off script to seed AppSettings table
├── deploy-sam.sh             # Local deploy helper script
│
├── config/
│   ├── settings.py           # Config class — reads all env vars
│   ├── otp.py                # OTPType constants, EMAIL/PHONE_OTP_TYPES, OTP_RESEND_COOLDOWN
│   └── permissions.py        # Role hierarchy + DEFAULT_RESOURCE_PERMISSIONS
│
├── handlers/                 # One file per feature area
│   ├── register.py           # POST /auth/register, POST /auth/register-master
│   ├── login.py              # POST /auth/login
│   ├── logout.py             # POST /auth/logout
│   ├── refresh_token.py      # POST /auth/refresh
│   ├── verify.py             # POST /auth/verify, POST /auth/resend-otp
│   ├── profile.py            # GET/PUT /auth/me
│   ├── users.py              # GET/POST/PUT/DELETE /users and /users/{id}
│   ├── settings.py           # GET/PUT /settings
│   └── permissions.py        # GET/PUT /permissions and /permissions/{resource}
│
├── middleware/
│   ├── auth.py               # @require_auth decorator (JWT validation + RBAC)
│   └── rate_limiting.py      # Per-IP and per-user rate limit decorators
│
├── utils/
│   ├── database.py           # DynamoDB wrappers: UserDB, RefreshTokenDB, etc.
│   ├── jwt_utils.py          # Token creation and validation
│   ├── password.py           # bcrypt hash/verify
│   ├── verification.py       # OTP generation, SES email delivery, masking helpers
│   ├── responses.py          # Standardised success_response / error_response
│   ├── validators.py         # Email, phone, password, name validators
│   ├── schemas.py            # Request body schemas (field definitions)
│   ├── schema_validator.py   # SchemaField, Schema, @validate_request_body
│   └── app_settings.py       # Runtime settings + resource permissions (60 s cache)
│
└── .github/workflows/
    ├── deploy-dev.yml
    ├── deploy-staging.yml
    ├── deploy-prod.yml
    ├── destroy-dev.yml
    ├── destroy-staging.yml
    └── destroy-prod.yml
```

---

## Request Flow

```
API Gateway → lambda_handler()
               ├── CORS preflight (OPTIONS) → return 200 immediately
               ├── match_route(method, path) → find handler function
               ├── middleware decorators run first (rate limit → auth → validate body)
               └── handler function → success_response / error_response
```

All responses share a standard envelope:
```json
{
  "success": true,
  "message": "...",
  "data": { ... },
  "error": null,
  "meta": {}
}
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/register | None | Public registration — email or phone (at least one) |
| POST | /auth/register-master | Secret key in body | Create master admin user |
| POST | /auth/verify | None | Submit OTP code (13 types via `otp_type`) |
| POST | /auth/resend-otp | None | Resend a pending OTP (60 s cooldown) |
| POST | /auth/login | None | Login by email or phone — returns access + refresh tokens |
| POST | /auth/refresh | Refresh token in body | Get new access token |
| POST | /auth/logout | JWT | Revoke refresh token |
| GET | /auth/me | JWT | Get own profile |
| PUT | /auth/me | JWT | Update profile (email/phone changes trigger OTP) |
| GET | /users | JWT (owner+) | List users |
| POST | /users | JWT (admin+) | Create internal user |
| GET | /users/{id} | JWT (owner+) | Get user by ID |
| PUT | /users/{id}/role | JWT (owner+) | Change user role |
| DELETE | /users/{id} | JWT (master) | Delete user |
| GET | /settings | JWT (owner+) | Get app settings |
| PUT | /settings | JWT (master) | Update app settings |
| GET | /permissions | JWT (master) | List all resource permission configs |
| GET | /permissions/{resource} | JWT (master) | Get one resource's operation→role map |
| PUT | /permissions/{resource} | JWT (master) | Replace a resource's config |
| POST | /permissions/seed | JWT (master) | Write code defaults to DynamoDB |

---

## Roles

Defined in `config/permissions.py`. Hierarchy: `master > admin > user > customer`

- **master** — full system access, cross-tenant
- **admin** — manage users within their tenant
- **user** — standard internal user, scoped to tenant
- **customer** — external public user, no tenant

---

## DynamoDB Tables

All tables are named `{APP_NAME}-{ENVIRONMENT}-{table}`, e.g. `community-fund-prod-users`.

| Table | Primary Key | GSI | TTL |
|-------|-------------|-----|-----|
| users | user_id (HASH) | email-index, phone-index (sparse) | No |
| refresh_tokens | token (HASH) | user_id-index | Yes (expires_at) |
| verification_codes | user_id (HASH) + code_type (RANGE) | No | No |
| login_attempts | ip_address (HASH) + timestamp (RANGE) | No | No |
| rate_limits | limit_key (HASH) | No | No |
| app_settings | setting_key (HASH) | No | No |

---

## Environment Variables

Set automatically by SAM from template.yaml parameters. For local dev, create `.env`:

```env
APP_NAME=basic-auth
ENVIRONMENT=dev
JWT_SECRET=<generate with: openssl rand -base64 32>
REFRESH_TOKEN_SECRET=<generate with: openssl rand -base64 32>
MASTER_SECRET_KEY=<generate with: openssl rand -base64 32>
AWS_REGION=eu-north-1
FROM_EMAIL=noreply@yourdomain.com
```

Do NOT commit `.env`. It is gitignored.

---

## GitHub Actions Secrets & Variables

**Variables** (Settings → Actions → Variables) — not sensitive, shown in logs:
| Name | Example |
|------|---------|
| `APP_NAME` | `basic-auth` |
| `AWS_REGION` | `eu-north-1` |
| `FROM_EMAIL` | `noreply@yourdomain.com` |

**Secrets** (Settings → Actions → Secrets) — masked in logs:
| Name | Used by |
|------|---------|
| `AWS_ACCESS_KEY_ID` | dev + staging deploy/destroy |
| `AWS_SECRET_ACCESS_KEY` | dev + staging deploy/destroy |
| `AWS_ACCESS_KEY_ID_PROD` | prod deploy/destroy |
| `AWS_SECRET_ACCESS_KEY_PROD` | prod deploy/destroy |
| `JWT_SECRET` | dev + staging |
| `REFRESH_TOKEN_SECRET` | dev + staging |
| `MASTER_SECRET_KEY` | dev + staging |
| `JWT_SECRET_PROD` | prod |
| `REFRESH_TOKEN_SECRET_PROD` | prod |
| `MASTER_SECRET_KEY_PROD` | prod |

---

## Local Development

```bash
# Install deps
pip install -r requirements.txt

# Run locally (simulates Lambda event)
python lambda_function.py

# Deploy to dev manually
sam build --use-container
sam deploy --stack-name basic-auth-dev --capabilities CAPABILITY_IAM --resolve-s3 \
  --parameter-overrides AppName=basic-auth Environment=dev \
  JWTSecret=<secret> RefreshTokenSecret=<secret> MasterSecretKey=<secret>
```

---

## Deployment

Handled entirely via GitHub Actions. All workflows are `workflow_dispatch` (manual only).

| Workflow | Trigger | Notes |
|----------|---------|-------|
| Deploy to Dev | Manual | No confirmation needed |
| Deploy to Staging | Manual | No confirmation needed |
| Deploy to Production | Manual | Must type `deploy-to-production` |
| Destroy Dev Environment | Manual | Must type `DESTROY` |
| Destroy Staging Environment | Manual | Must type `DESTROY` |
| Destroy Production Environment | Manual | Must type `DESTROY-PRODUCTION`, requires environment approval |

---

## Growth Expectations

This system is designed to grow significantly. Keep this in mind on every change:

**Many more endpoints are coming.** Each new domain feature (bookings, products, schedules,
invoices, etc.) adds handlers, schemas, routes, and SAM events. Design every piece to be
added to, not rewritten.

**Patterns to follow when adding an endpoint:**
1. Add a resource + operation pair to `DEFAULT_RESOURCE_PERMISSIONS` in `config/permissions.py`
2. Create schema in `utils/schemas.py`, register it in `ROUTE_SCHEMAS`
3. Write handler in the appropriate `handlers/` file
4. Add route to `ROUTES` dict in `lambda_function.py`
5. Add API Gateway event + swagger path in `template.yaml`
6. Use `@require_auth(resource='<resource>', operation='<operation>')` — never hardcode role strings
7. After deploying, call `POST /permissions/seed` to write new defaults to DynamoDB

**Cache behaviour.** Permission changes via the API take effect immediately (write-through
cache with fresh TTL). Manual DynamoDB edits propagate to warm Lambda containers within
60 seconds. Settings cache works the same way.

**Secure by default.** Any new permission check that has no DB record and no code default
should **deny**, not silently allow. Never add a fallback that grants access.

---

## Known Issues & Tech Debt

See `docs/next-steps.md` for the full prioritised list. Critical items:

1. `lambda_function.py` logs the master secret key and full request body to CloudWatch on every request — remove all debug `print` statements before handling real users
2. `LoginAttemptDB.count_recent_attempts` queries a GSI that does not exist — remove the `IndexName` parameter
3. SMS OTP delivery is still a stub (`send_sms_otp` logs to CloudWatch, does not call SNS) — implement SNS integration
4. `datetime.utcnow()` is deprecated in Python 3.12 — replace with `datetime.now(timezone.utc)`
5. `forgot_password` OTP verification sets a `password_reset_verified` flag but there is no `POST /auth/reset-password` endpoint yet to consume it

---

## Multi-Tenant / White-Label Usage

To deploy a second isolated instance:
1. Change `APP_NAME` in GitHub Variables (or pass `--parameter-overrides AppName=hotel-manager`)
2. Run Deploy workflow
3. All DynamoDB tables and Lambda function get the new prefix automatically
4. No code changes needed
