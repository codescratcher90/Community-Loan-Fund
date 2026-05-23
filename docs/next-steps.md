# Next Steps — Basic-Auth Improvement Plan

Findings from code review conducted May 2026.
Items are ordered by risk within each phase.

---

## Phase 1 — Fix What's Broken
> Do this before any real user traffic. These are bugs or active security holes.

### 1.1 Remove debug logs leaking secrets to CloudWatch

**Files:** `lambda_function.py:101-139`, `handlers/register.py:52,135,139,151-154`

`lambda_function.py` line 139 prints the master secret key on every single request:
```python
print("SECRET_KEY from env:", secret_key)  # DELETE THIS
```
Line 104 dumps the entire Lambda event (including Authorization headers and request bodies):
```python
print("Incoming event:", json.dumps(event))  # DELETE THIS
```
`register.py` line 135 prints the raw event (includes secret_key in body):
```python
print("RAW EVENT BODY:", event)  # DELETE THIS
```
Remove all debug `print` statements that log request data, secrets, or internal state.
Replace with structured logging only where genuinely needed.

---

### 1.2 Fix the LoginAttempts GSI bug

**File:** `utils/database.py:280`

`count_recent_attempts` queries `IndexName='ip_address-timestamp-index'` which does not
exist in `template.yaml`. The table's own primary key is already `ip_address (HASH) +
timestamp (RANGE)`, so no GSI is needed. Remove the `IndexName` parameter:

```python
# Before
response = login_attempts_table.query(
    IndexName='ip_address-timestamp-index',
    KeyConditionExpression=...
)

# After
response = login_attempts_table.query(
    KeyConditionExpression=...
)
```

This currently throws `ResourceNotFoundException` on every IP-based rate limit check.

---

### 1.3 Replace `datetime.utcnow()` throughout

**Files:** `utils/database.py`, `handlers/register.py`, `handlers/login.py`,
`utils/verification.py`, `utils/app_settings.py`

`datetime.utcnow()` is deprecated in Python 3.12 (the current runtime). Replace all
occurrences with `datetime.now(timezone.utc)` and add `from datetime import timezone`
to each file.

---

### 1.4 Add TTL to VerificationCodesTable

**File:** `template.yaml` — `VerificationCodesTable` resource

The table stores OTP codes but has no TTL. Expired codes accumulate forever.
The code already sets an `expires_at` field — just enable TTL in the table definition:

```yaml
VerificationCodesTable:
  ...
  TimeToLiveSpecification:
    Enabled: true
    AttributeName: expires_at
```

---

### 1.5 Add TTL to LoginAttemptsTable

**File:** `template.yaml` — `LoginAttemptsTable` resource

Login attempt records are never cleaned up. Add a TTL so old records expire automatically.
The code will need to store an `expires_at` (or `ttl`) epoch attribute when recording attempts.

---

## Phase 2 — Security Hardening
> Correct but exploitable under specific conditions.

### 2.1 Use constant-time comparison for master key

**File:** `handlers/register.py`

String equality (`!=`) is not constant-time and leaks information via timing attacks.

```python
# Before
if not secret_key or secret_key != expected_key:

# After
import secrets
if not secret_key or not secrets.compare_digest(secret_key, expected_key):
```

---

### 2.2 Raise minimum password length

**File:** `config/settings.py`

```python
# Before
MIN_PASSWORD_LENGTH: int = 4

# After
MIN_PASSWORD_LENGTH: int = 8  # minimum; 12 recommended for production
```

Consider also enforcing complexity (uppercase, number, symbol) via the validator.

---

### 2.3 Make CORS origin configurable

**Files:** `lambda_function.py`, `template.yaml`

`Access-Control-Allow-Origin: *` allows any domain. For production, restrict to your
actual frontend domain. Add an `AllowedOrigin` SAM parameter and thread it through
as an environment variable.

---

### 2.4 Rate limiter should fail closed

**File:** `utils/database.py`

On any DynamoDB error, the rate limiter silently allows all requests:
```python
except Exception as e:
    print(f"Rate limit check error: {str(e)}")
    return True  # fail open — dangerous
```
Change to fail closed (return `False`) or implement a fallback in-memory counter.
At minimum, add a CloudWatch metric/alarm when this path is hit.

---

### 2.5 Fix race condition on user registration

**Files:** `handlers/register.py`, `utils/database.py`

Two simultaneous registrations with the same email both pass the `get_user_by_email`
check and both successfully create a user (duplicate emails). Fix with a DynamoDB
conditional write:

```python
users_table.put_item(
    Item=user_data,
    ConditionExpression='attribute_not_exists(email)'
)
```
This requires email to be queryable as a key — alternatively use the GSI and catch
`ConditionalCheckFailedException`.

---

## Phase 3 — Complete Unfinished Features

### 3.1 Implement SMS verification via SNS

**File:** `utils/verification.py` — `send_sms_otp()`

`send_sms_otp()` logs to CloudWatch but does not call SNS. The function signature,
OTP record creation, and resend logic are all in place — only the delivery step is
missing:

- Add SNS publish permission to Lambda IAM policy in `template.yaml`
- Replace the stub body with a `boto3` SNS client `publish()` call

Consider that SNS SMS has per-message costs.

---

### 3.2 Implement POST /auth/reset-password

The `forgot_password` OTP type is fully wired: `POST /auth/verify` with
`otp_type: "forgot_password"` sets `password_reset_verified = true` with a
10-minute expiry (`password_reset_expires_at`). What's missing is the endpoint
that consumes this flag:

```
POST /auth/reset-password
  body: { user_id, new_password }
  checks: password_reset_verified == true and password_reset_expires_at not expired
  action: hash + store new password, clear the reset flag
```

Until this is added, the forgot-password flow is incomplete and `password_reset_verified`
accumulates stale flags in the users table.

---

### 3.3 Add pagination to list endpoints

**File:** `utils/database.py`

`list_users` uses DynamoDB `scan` with `Limit`. DynamoDB's `Limit` caps items
*scanned*, not *returned* — with filter expressions you often get fewer items than
requested with no signal that more exist.

Fix: propagate `LastEvaluatedKey` as a pagination cursor in the API response, and
accept an `exclusive_start_key` query parameter to fetch the next page.

---

### 3.4 Replace scan-based list operations with GSI queries

**File:** `utils/database.py`

For multi-tenant filtering, a full table scan is expensive at scale. Add a GSI on
`tenant_id` to `UsersTable` in `template.yaml` and use `query` instead of `scan`.

---

## Phase 4 — Tests
> There are currently zero tests in the project. Auth infrastructure is the highest-risk
> area to ship without tests.

### 4.1 Unit tests for core auth logic

Using `pytest`. Priority test targets:
- `utils/password.py` — hash and verify
- `utils/jwt_utils.py` — token creation, expiry, invalid signature
- `utils/verification.py` — OTP generation, masking, cooldown logic
- `utils/database.py` — mock DynamoDB with `moto`, test all DB classes
- `handlers/register.py` — valid registration, duplicate email, bad secret key
- `handlers/login.py` — correct password, wrong password, locked account, unverified account

### 4.2 Integration tests for auth flows

End-to-end flows against a local DynamoDB (via `moto` or a local DynamoDB Docker image):
- Register → Verify OTP → Login → Refresh → Logout
- Register → Login fail 5× → account locked → wait for auto-unlock → login succeeds
- Register master → create internal user → assign role → login as that user
- PUT /auth/me with email change → verify OTP → confirm new email is applied

### 4.3 Add tests to CI

Add a `test.yml` GitHub Actions workflow that runs `pytest` on every push to any branch.
Gate PRs on test passing.

---

## Tracking

| Phase | Status |
|-------|--------|
| Phase 1 — Fix What's Broken | Not started |
| Phase 2 — Security Hardening | Not started |
| Phase 3 — Complete Features | Not started |
| Phase 4 — Tests | Not started |
