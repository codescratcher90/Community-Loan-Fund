# Basic Auth API

A production-ready, serverless authentication API built on AWS Lambda, API Gateway, and DynamoDB.
White-label and reusable — deploy multiple isolated instances in the same AWS account by changing one variable.

## Features

- JWT access + refresh tokens (PyJWT + bcrypt)
- 8-tier role hierarchy with multi-tenant isolation
- Dynamic runtime permissions — master can grant/revoke actions per role without redeploying
- Email & SMS OTP verification
- Account locking, rate limiting, failed-login tracking
- Fully serverless — pay per request, zero servers to manage
- Multi-environment: dev / staging / production

## Architecture

```
API Client → API Gateway → Lambda → DynamoDB
```

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 on AWS Lambda |
| API | AWS API Gateway (REST) |
| Database | AWS DynamoDB (6 tables) |
| Auth | JWT + bcrypt |
| IaC | AWS SAM |
| CI/CD | GitHub Actions |

## Quick Start

```bash
# 1. Register a master user
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{"secret_key":"YOUR_MASTER_SECRET","email":"admin@example.com","password":"SecurePass123","first_name":"Admin","last_name":"User"}'

# 2. Login
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"SecurePass123"}'

# 3. Use the access token
curl -X GET $API_URL/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Roles

| Role | Level | Scope |
|---|---|---|
| master | 8 | System — cross-tenant |
| owner | 7 | Tenant |
| admin | 6 | Tenant |
| manager | 5 | Tenant |
| supervisor | 4 | Tenant |
| coordinator | 3 | Tenant |
| staff | 2 | Tenant |
| customer | 1 | Global — no tenant |

Generic roles map to any job title in your domain (hotel, clinic, gym, SaaS...).
See [docs/architecture.md](docs/architecture.md) for the full permission matrix.

## Documentation

| Doc | Contents |
|---|---|
| [docs/api-reference.md](docs/api-reference.md) | All endpoints, request/response examples, error codes |
| [docs/architecture.md](docs/architecture.md) | System design, role hierarchy, permissions, DB tables |
| [docs/deployment.md](docs/deployment.md) | GitHub Actions setup, APP_NAME / white-label guide, local deploy |
| [docs/examples.md](docs/examples.md) | Real-world use cases: hotel, gym, SaaS, clinic, e-learning |
| [docs/next-steps.md](docs/next-steps.md) | Improvement plan — known bugs, security hardening, features |
| [CLAUDE.md](CLAUDE.md) | Project context for AI-assisted development |

## Local Development

```bash
pip install -r requirements.txt

# Set up .env
cp .env.example .env   # fill in JWT_SECRET, MASTER_SECRET_KEY, etc.

# Run locally (simulates Lambda)
python lambda_function.py

# Deploy to dev
./deploy-sam.sh
```

## Contributing

1. Fork → feature branch → PR
2. Run the existing tests before pushing (see `docs/next-steps.md §4` for planned test suite)

## License

MIT
