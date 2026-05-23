# Deployment Guide

Two ways to deploy: **GitHub Actions** (recommended — zero local tools needed) or **manual** with SAM CLI.

---

## Prerequisites (Manual Deploy Only)

| Tool | Check | Install |
|---|---|---|
| AWS CLI v2 | `aws --version` | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| AWS SAM CLI | `sam --version` | [SAM install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) |
| Docker | `docker --version` | [docker.com](https://docs.docker.com/get-docker/) |

---

## Option 1: GitHub Actions (Recommended)

### Step 1 — Create an IAM User in AWS

1. AWS Console → IAM → Users → **Add users**
2. Name: `github-actions-deploy`
3. Access type: **Programmatic access**
4. Attach this custom policy (or the managed policies listed below):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "cloudformation:*",
      "lambda:*",
      "apigateway:*",
      "dynamodb:*",
      "iam:CreateRole", "iam:DeleteRole", "iam:PutRolePolicy",
      "iam:DeleteRolePolicy", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
      "iam:GetRole", "iam:PassRole",
      "s3:*"
    ],
    "Resource": "*"
  }]
}
```

Equivalent managed policies: `AWSLambda_FullAccess`, `AmazonAPIGatewayAdministrator`,
`AmazonDynamoDBFullAccess`, `AWSCloudFormationFullAccess`, `IAMFullAccess`, `AmazonS3FullAccess`.

5. **Save the credentials** — you will not see them again:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### Step 2 — Generate Secrets

```bash
openssl rand -base64 32   # → JWT_SECRET
openssl rand -base64 32   # → REFRESH_TOKEN_SECRET
openssl rand -base64 32   # → MASTER_SECRET_KEY
```

Generate a separate set for production.

### Step 3 — Add Variables and Secrets to GitHub

Go to **Settings → Secrets and variables → Actions**.

#### Variables tab (non-sensitive — visible in logs)

| Variable | Example | Notes |
|---|---|---|
| `APP_NAME` | `basic-auth` | Determines all resource names (see [APP_NAME guide](#app_name--white-label-deployments)) |
| `AWS_REGION` | `eu-north-1` | Not a secret — stored as variable so it appears unmasked in deployment URLs |

#### Secrets tab (sensitive — masked in logs)

**Dev / Staging:**

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `JWT_SECRET` | JWT signing secret |
| `REFRESH_TOKEN_SECRET` | Refresh token signing secret |
| `MASTER_SECRET_KEY` | Secret for `POST /auth/register-master` |

**Production** (separate credentials recommended):

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID_PROD` | Production IAM access key |
| `AWS_SECRET_ACCESS_KEY_PROD` | Production IAM secret key |
| `JWT_SECRET_PROD` | Production JWT secret |
| `REFRESH_TOKEN_SECRET_PROD` | Production refresh secret |
| `MASTER_SECRET_KEY_PROD` | Production master secret |

### Step 4 — Configure GitHub Environment (Production Only)

1. Settings → **Environments** → **New environment** → name it `production`
2. Add protection rules:
   - Required reviewers
   - Wait timer: 5 minutes
   - Deployment branches: only protected branches

### Step 5 — Run a Workflow

All workflows are **manual** (`workflow_dispatch`):

| Workflow | Trigger confirmation | AWS credentials used |
|---|---|---|
| Deploy to Dev | None | `AWS_ACCESS_KEY_ID` |
| Deploy to Staging | None | `AWS_ACCESS_KEY_ID` |
| Deploy to Production | Must type `deploy-to-production` | `AWS_ACCESS_KEY_ID_PROD` |
| Destroy Dev | Must type `DESTROY` | `AWS_ACCESS_KEY_ID` |
| Destroy Staging | Must type `DESTROY` | `AWS_ACCESS_KEY_ID` |
| Destroy Production | Must type `DESTROY-PRODUCTION` | `AWS_ACCESS_KEY_ID_PROD` |

Go to **Actions → [workflow name] → Run workflow**.

### Getting Your API URL After Deployment

**Method 1:** Workflow summary in Actions tab (shown automatically)

**Method 2:** AWS CLI
```bash
aws cloudformation describe-stacks \
  --stack-name {APP_NAME}-{env} \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

**Method 3:** AWS Console → CloudFormation → Stacks → `{APP_NAME}-{env}` → Outputs

---

## APP_NAME & White-Label Deployments

`APP_NAME` controls the name of every AWS resource created. Change it to deploy a completely isolated instance in the same AWS account — no code changes needed.

### Naming Pattern

```
{APP_NAME}-{ENVIRONMENT}-{resource}
```

| APP_NAME | Environment | Stack | Lambda | DynamoDB users table |
|---|---|---|---|---|
| `basic-auth` | `dev` | `basic-auth-dev` | `basic-auth-dev-api` | `basic-auth-dev-users` |
| `hotel-manager` | `prod` | `hotel-manager-prod` | `hotel-manager-prod-api` | `hotel-manager-prod-users` |
| `restaurant-pos` | `prod` | `restaurant-pos-prod` | `restaurant-pos-prod-api` | `restaurant-pos-prod-users` |

### APP_NAME Validation Rules

- Lowercase alphanumeric + hyphens only
- Must start and end with an alphanumeric character
- ✅ `hotel-manager`, `my-app-123`, `saas-platform`
- ❌ `HotelManager` (uppercase), `-myapp` (leading hyphen), `my_app` (underscore)

### Multi-Client Setup Options

**Option A — Branches** (recommended)
```bash
git checkout -b client/hotel
# Set APP_NAME=hotel-manager in GitHub Variables
# Deploy from this branch
```

**Option B — Separate repositories**
Fork for each client, set different `APP_NAME` per repo.

**Option C — Workflow input** (advanced)
Modify workflow to accept `app_name` as `workflow_dispatch` input:
```yaml
on:
  workflow_dispatch:
    inputs:
      app_name:
        description: 'Application name'
        default: 'basic-auth'
env:
  APP_NAME: ${{ github.event.inputs.app_name || vars.APP_NAME || 'basic-auth' }}
```

Multiple deployments in the same AWS account coexist with zero conflicts because every resource name includes `APP_NAME`.

---

## Option 2: Manual Deployment (Local)

### 1. Configure AWS credentials

```bash
aws configure
aws sts get-caller-identity   # verify
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env:
APP_NAME=basic-auth
ENVIRONMENT=dev
JWT_SECRET=$(openssl rand -base64 32)
REFRESH_TOKEN_SECRET=$(openssl rand -base64 32)
MASTER_SECRET_KEY=$(openssl rand -base64 32)
AWS_REGION=eu-north-1
```

### 3. Deploy

```bash
# Interactive (prompts for APP_NAME and ENVIRONMENT)
./deploy-sam.sh

# Or pass directly
APP_NAME=hotel-manager ENVIRONMENT=prod ./deploy-sam.sh
```

The script validates prerequisites, builds, deploys, and prints the API URL.

### Local API Server (SAM Local)

```bash
pip install -r requirements.txt
sam local start-api              # requires Docker
sam local invoke AuthFunction --event events/test-event.json
```

---

## Multi-Environment Strategy

| Environment | Purpose | AWS credentials |
|---|---|---|
| `dev` | Feature development, daily work | Dev IAM user |
| `staging` | Pre-release integration testing | Dev IAM user |
| `prod` | Live users | Separate prod IAM user (recommended separate account) |

Use different secrets for each environment. Never share `JWT_SECRET` across environments.

---

## Monitoring

### CloudWatch Logs

```bash
# Lambda logs (replace with your app name)
aws logs tail /aws/lambda/basic-auth-dev-api --follow

# Last 100 lines
aws logs tail /aws/lambda/basic-auth-dev-api --since 1h
```

Key metrics to monitor in CloudWatch:
- Lambda: invocations, errors, duration, throttles
- API Gateway: 4xx/5xx count, latency
- DynamoDB: consumed capacity, throttles

---

## Cleanup / Destroy

### Via GitHub Actions

Use the **Destroy** workflows (requires typing a confirmation string).

### Via AWS CLI

```bash
# Delete a specific stack (and all its resources)
aws cloudformation delete-stack --stack-name basic-auth-dev

# Or with SAM CLI
sam delete --stack-name basic-auth-dev
```

> **Warning:** This deletes all DynamoDB tables and all data in them. Back up if needed.

---

## Security Best Practices

**Credentials:**
- Use separate IAM users for dev/staging vs production
- Rotate secrets regularly (`openssl rand -base64 32`)
- Enable MFA on all AWS accounts
- Never commit `.env` — it is gitignored

**GitHub:**
- Enable branch protection on `main` and `staging`
- Use GitHub Environments with required reviewers for production
- Never put `APP_NAME` or `AWS_REGION` in Secrets — they are variables (non-sensitive)

**AWS:**
- Use separate AWS accounts for production (full isolation)
- Enable CloudTrail for audit logging
- Review IAM permissions — avoid `*` on resource ARNs in production

---

## Troubleshooting

<details>
<summary>Error: AWS credentials not configured</summary>

```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=eu-north-1
```

In GitHub Actions: verify secrets are in **Secrets** tab, not Variables. No spaces or newlines.
</details>

<details>
<summary>Error: Access Denied / Forbidden</summary>

The IAM user needs more permissions. Attach the policies listed in Step 1, then wait 1–2 minutes for propagation.
</details>

<details>
<summary>Error: Stack already exists</summary>

This is fine — SAM updates the existing stack.
</details>

<details>
<summary>Error: No changes to deploy</summary>

Also fine — infrastructure is already up to date.
</details>

<details>
<summary>Workflow still uses `basic-auth` after changing APP_NAME</summary>

Make sure `APP_NAME` is in the **Variables** tab, not Secrets. Variables are unmasked and available as `vars.APP_NAME`.
</details>

<details>
<summary>Stack name mismatch after renaming APP_NAME</summary>

Delete the old stack first:
```bash
aws cloudformation delete-stack --stack-name old-name-dev
```
Then deploy with the new name — it creates a fresh stack.
</details>

<details>
<summary>SAM CLI or Docker not found</summary>

- SAM: `brew install aws-sam-cli` (macOS) or [official guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Docker: [docker.com/get-docker](https://docs.docker.com/get-docker/)
- Linux Docker: `sudo systemctl start docker`
</details>
