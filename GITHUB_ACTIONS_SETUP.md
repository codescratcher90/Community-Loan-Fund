# GitHub Actions Setup Guide 🚀

Complete guide to set up automatic deployment to AWS using GitHub Actions.

## 📋 Overview

This repository uses GitHub Actions to automatically deploy to AWS when you push code:

| Branch/Tag | Environment | Workflow | Trigger |
|------------|-------------|----------|---------|
| `main` or `develop` | Dev | `deploy-dev.yml` | Push to branch |
| `staging` | Staging | `deploy-staging.yml` | Push to branch |
| `v*.*.*` tags | Production | `deploy-prod.yml` | Push tag or manual |

## 🔧 Step-by-Step Setup

### Step 1: Get AWS Credentials

#### Option A: Create IAM User (Recommended)

1. Go to **AWS Console → IAM → Users**
2. Click **Add users**
3. User name: `github-actions-deploy`
4. Select: **Access key - Programmatic access**
5. Click **Next: Permissions**

#### Attach Policies:
Add these managed policies:
- `AWSLambda_FullAccess`
- `AmazonAPIGatewayAdministrator`
- `AmazonDynamoDBFullAccess`
- `AWSCloudFormationFullAccess`
- `IAMFullAccess`
- `AmazonS3FullAccess`

Or create a custom policy (more secure):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "apigateway:*",
        "dynamodb:*",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "s3:*"
      ],
      "Resource": "*"
    }
  ]
}
```

6. Click **Next** → **Next** → **Create user**
7. **SAVE THESE CREDENTIALS** (you won't see them again!):
   - Access Key ID: `AKIAIOSFODNN7EXAMPLE`
   - Secret Access Key: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

#### Option B: Use Existing IAM Role (Advanced)

Configure OIDC for GitHub Actions (more secure, no long-lived credentials).

---

### Step 2: Generate Secrets

Generate strong secrets for JWT tokens:

```bash
# Run these commands and save the outputs
openssl rand -base64 32  # For JWT_SECRET
openssl rand -base64 32  # For REFRESH_TOKEN_SECRET
openssl rand -base64 32  # For MASTER_SECRET_KEY
```

Example outputs (DO NOT use these, generate your own!):
```
JWT_SECRET: kX8fJ2mN9pL3qR5tV7wY0zB4cD6eG8hI
REFRESH_TOKEN_SECRET: A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
MASTER_SECRET_KEY: Z9Y8X7W6V5U4T3S2R1Q0P9O8N7M6L5K4
```

---

### Step 3: Add Secrets and Variables to GitHub

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**

#### 3a. Add Variables (Non-Sensitive Configuration)

Click the **Variables** tab:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `APP_NAME` | `basic-auth` or your custom name | Application name for resource naming |

**Example custom names:**
- `hotel-manager` - For hotel management system
- `restaurant-pos` - For restaurant POS
- `gymflow` - For gym management

> 💡 **White-Label Deployments:** Change `APP_NAME` to deploy multiple instances!
> See **[GITHUB_ACTIONS_APP_NAME.md](GITHUB_ACTIONS_APP_NAME.md)** for details.

#### 3b. Add Secrets (Sensitive Data)

Click the **Secrets** tab and add:

##### For Dev/Staging:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_ACCESS_KEY_ID` | Your AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | Your AWS Secret Access Key | `wJalrXUtnFEMI/K7MDENG...` |
| `AWS_REGION` | Your AWS region | `eu-north-1` |
| `JWT_SECRET` | Generated secret | `kX8fJ2mN9pL3qR5tV7wY0zB4cD6eG8hI` |
| `REFRESH_TOKEN_SECRET` | Generated secret | `A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6` |
| `MASTER_SECRET_KEY` | Generated secret | `Z9Y8X7W6V5U4T3S2R1Q0P9O8N7M6L5K4` |

#### For Production (Separate AWS Account - Recommended):

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_ACCESS_KEY_ID_PROD` | Production AWS Access Key ID | `AKIAI...` |
| `AWS_SECRET_ACCESS_KEY_PROD` | Production AWS Secret Key | `wJal...` |
| `JWT_SECRET_PROD` | Different JWT secret for prod | Generate new |
| `REFRESH_TOKEN_SECRET_PROD` | Different refresh secret | Generate new |
| `MASTER_SECRET_KEY_PROD` | Different master secret | Generate new |

**Screenshots for adding secrets:**

```
GitHub Repo → Settings → Secrets and variables → Actions → New repository secret

Name: AWS_ACCESS_KEY_ID
Secret: AKIAIOSFODNN7EXAMPLE
[Add secret]
```

---

### Step 4: Configure GitHub Environments (Optional for Prod)

For production protection:

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Configure protection rules:
   - ✅ Required reviewers (select team members)
   - ✅ Wait timer: 5 minutes
   - ✅ Deployment branches: Only protected branches

---

### Step 5: Test Deployment

#### Test Dev Deployment:

```bash
# Push to main or develop branch
git checkout main
git add .
git commit -m "Test deployment"
git push origin main
```

Then:
1. Go to **Actions** tab in GitHub
2. Watch the **Deploy to Dev** workflow
3. After success, check the summary for your API URL

#### Test Staging Deployment:

```bash
# Create and push to staging branch
git checkout -b staging
git push origin staging
```

#### Test Production Deployment:

```bash
# Create a version tag
git tag v1.0.0
git push origin v1.0.0
```

Or manually trigger:
1. Go to **Actions** → **Deploy to Production**
2. Click **Run workflow**
3. Type `deploy-to-production` to confirm
4. Click **Run workflow**

---

## 🔍 How It Works

### Dev Workflow (`deploy-dev.yml`)

**Triggers:**
- Manual trigger from Actions tab

**Steps:**
1. Checkout code
2. Configure AWS credentials
3. Install Python & SAM CLI
4. Validate SAM template
5. Build with Docker
6. Deploy to AWS dev environment
7. Output API URL

**Stack created:** `{APP_NAME}-dev` (default: `basic-auth-dev`)

**Example with custom APP_NAME:**
- `APP_NAME=hotel-manager` → Stack: `hotel-manager-dev`
- `APP_NAME=restaurant-pos` → Stack: `restaurant-pos-dev`

### Staging Workflow (`deploy-staging.yml`)

**Triggers:**
- Manual trigger from Actions tab

**Stack created:** `{APP_NAME}-staging` (default: `basic-auth-staging`)

### Production Workflow (`deploy-prod.yml`)

**Triggers:**
- Manual trigger (requires confirmation)

**Extra protections:**
- Requires typing "deploy-to-production" to confirm
- Uses separate AWS credentials (`AWS_ACCESS_KEY_ID_PROD`)
- Uses separate secrets (production secrets)
- Optional: Requires reviewer approval (if environment configured)

**Stack created:** `{APP_NAME}-prod` (default: `basic-auth-prod`)

---

### 🏷️ Resource Naming

All AWS resources are named using: **`{APP_NAME}-{ENVIRONMENT}-{resource}`**

**Default** (`APP_NAME=basic-auth`):
- Stack: `basic-auth-dev`
- Tables: `basic-auth-dev-users`, `basic-auth-dev-tokens`
- Lambda: `basic-auth-dev-api`
- API Gateway: `basic-auth-dev-api`

**Custom** (`APP_NAME=hotel-manager`):
- Stack: `hotel-manager-dev`
- Tables: `hotel-manager-dev-users`, `hotel-manager-dev-tokens`
- Lambda: `hotel-manager-dev-api`
- API Gateway: `hotel-manager-dev-api`

---

## 📊 Monitoring Deployments

### View Logs:

1. Go to **Actions** tab
2. Click on a workflow run
3. Click on the job name
4. Expand steps to see logs

### Check Deployment Status:

GitHub Actions will show:
- ✅ Build status
- ✅ Deployment status
- ✅ API URL in summary
- ✅ Errors if any

### Get API URL After Deployment:

**Method 1:** Check workflow summary in Actions tab

**Method 2:** AWS Console
```
CloudFormation → Stacks → {APP_NAME}-dev → Outputs → ApiUrl
```

**Method 3:** AWS CLI
```bash
# Replace {APP_NAME} with your actual app name
aws cloudformation describe-stacks \
  --stack-name {APP_NAME}-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text

# Example for hotel-manager:
aws cloudformation describe-stacks \
  --stack-name hotel-manager-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Use separate AWS accounts for dev/staging/prod
- Use different secrets for each environment
- Rotate secrets regularly
- Enable MFA on AWS accounts
- Use minimal IAM permissions
- Enable GitHub branch protection
- Use GitHub Environments for production
- Review deployment logs

### ❌ DON'T:
- Commit `.env` file
- Share AWS credentials
- Use same secrets across environments
- Disable security checks
- Deploy to production without review

---

## 🎨 White-Label / Multi-Client Deployments

Deploy the **same codebase** for **multiple clients** using custom `APP_NAME`:

### Scenario: Multiple Hotel Clients

**Client A - Luxury Hotels:**
1. Set `APP_NAME=luxury-hotels`
2. Deploy → Creates `luxury-hotels-prod`
3. API URL: `https://xxx.execute-api.region.amazonaws.com/prod/`

**Client B - Budget Hotels:**
1. Set `APP_NAME=budget-hotels`
2. Deploy → Creates `budget-hotels-prod`
3. API URL: `https://yyy.execute-api.region.amazonaws.com/prod/`

**Both deployments:**
- ✅ Run in the same AWS account
- ✅ Use separate databases
- ✅ Have independent APIs
- ✅ Zero conflicts

### Implementation Options:

**Option 1: Branches** (Recommended)
```bash
# Create branch for each client
git checkout -b client/luxury-hotels
# Set APP_NAME=luxury-hotels in GitHub Variables for this branch
# Deploy from this branch

git checkout -b client/budget-hotels
# Set APP_NAME=budget-hotels in GitHub Variables
# Deploy from this branch
```

**Option 2: Separate Repositories**
- Fork the repo for each client
- Set different `APP_NAME` in each repo's variables
- Deploy independently

**Option 3: Manual Workflow Input** (Advanced)
- Modify workflows to accept `APP_NAME` as input
- Select name when running workflow

📖 **Full Guide:** [GITHUB_ACTIONS_APP_NAME.md](GITHUB_ACTIONS_APP_NAME.md)

---

## 🐛 Troubleshooting

### Error: "AWS credentials not configured"

**Fix:** Check that secrets are added correctly:
- Go to Settings → Secrets and variables → Actions
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` exist
- No spaces or extra characters in secret values

### Error: "Access Denied" or "Forbidden"

**Fix:** IAM user needs more permissions
- Add required policies (CloudFormation, Lambda, API Gateway, DynamoDB, IAM, S3)
- Wait 1-2 minutes for permissions to propagate

### Error: "Stack already exists"

**Fix:** This is OK - SAM will update the existing stack

### Error: "No changes to deploy"

**Fix:** This is OK - means infrastructure is already up-to-date

### Workflow doesn't trigger

**Fix:**
- Check branch name matches workflow trigger
- Check workflow file syntax (YAML indentation)
- Check if Actions are enabled in repo settings

---

## 🔄 Workflow Examples

### Deploy to Dev Automatically:

```bash
git checkout main
# Make changes
git add .
git commit -m "Add new feature"
git push origin main
# ✅ Automatically deploys to dev
```

### Deploy to Staging:

```bash
git checkout staging
git merge main
git push origin staging
# ✅ Automatically deploys to staging
```

### Deploy to Production (Tag):

```bash
# After testing in staging
git checkout main
git tag v1.0.0
git push origin v1.0.0
# ✅ Automatically deploys to production
```

### Manual Production Deploy:

1. Go to GitHub → Actions → "Deploy to Production"
2. Click "Run workflow"
3. Select branch
4. Type `deploy-to-production`
5. Click "Run workflow"

---

## 📝 Quick Setup Checklist

- [ ] Create IAM user in AWS with required permissions
- [ ] Generate 3 secure secrets (JWT, Refresh, Master)
- [ ] Add **Variable** to GitHub (Settings → Actions → Variables):
  - [ ] `APP_NAME` (e.g., `basic-auth`, `hotel-manager`, or custom name)
- [ ] Add **Secrets** to GitHub (Settings → Actions → Secrets):
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
  - [ ] `AWS_REGION`
  - [ ] `JWT_SECRET`
  - [ ] `REFRESH_TOKEN_SECRET`
  - [ ] `MASTER_SECRET_KEY`
- [ ] (Optional) Create `production` environment in GitHub
- [ ] Go to Actions tab → Deploy to Dev → Run workflow
- [ ] Check Actions tab for deployment status
- [ ] Get API URL from workflow summary
- [ ] Test API endpoints

---

## 🎯 Summary

**Setup once:**
1. Create IAM user in AWS
2. Generate secrets
3. Add `APP_NAME` variable to GitHub
4. Add secrets to GitHub

**Deploy easily:**
- Go to Actions → Deploy to Dev → Run workflow
- Go to Actions → Deploy to Staging → Run workflow
- Go to Actions → Deploy to Production → Run workflow (with confirmation)

**White-label support:**
- Change `APP_NAME` variable for each client
- Deploy multiple instances in same AWS account
- Zero conflicts, isolated databases

**Zero manual AWS configuration needed!** 🎉

---

## 📞 Need Help?

- Check workflow logs in Actions tab
- Review AWS CloudFormation events in AWS Console
- Check IAM permissions
- Verify secrets are correct
- See main [README.md](README.md) for API documentation
