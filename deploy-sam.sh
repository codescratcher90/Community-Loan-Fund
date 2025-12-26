#!/bin/bash

# ========================================
# AWS SAM Deployment Script
# ========================================
# This script builds and deploys the Basic Auth API using AWS SAM
# It supports multiple environments (dev, staging, prod)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# Functions
# ========================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        echo "Visit: https://aws.amazon.com/cli/"
        exit 1
    fi
    print_success "AWS CLI found"

    # Check SAM CLI
    if ! command -v sam &> /dev/null; then
        print_error "AWS SAM CLI not found. Please install it first."
        echo "Visit: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
        exit 1
    fi
    print_success "AWS SAM CLI found"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid."
        echo "Run: aws configure"
        exit 1
    fi
    print_success "AWS credentials configured"

    # Display AWS account info
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-east-1")
    print_info "AWS Account: $AWS_ACCOUNT"
    print_info "AWS Region: $AWS_REGION"
}

load_environment() {
    local ENV=$1

    print_header "Loading Environment Configuration"

    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your configuration before deploying!"
            echo ""
            echo "Required steps:"
            echo "1. Edit .env file and set all secrets (JWT_SECRET, REFRESH_TOKEN_SECRET, MASTER_SECRET_KEY)"
            echo "2. Run this script again"
            exit 1
        else
            print_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi

    # Load .env file
    export $(cat .env | grep -v '^#' | xargs)
    print_success "Environment variables loaded from .env"

    # Validate critical secrets
    if [[ "$JWT_SECRET" == *"change-this"* ]] || [[ "$REFRESH_TOKEN_SECRET" == *"change-this"* ]] || [[ "$MASTER_SECRET_KEY" == *"your-super-secret"* ]]; then
        print_error "Default secrets detected in .env file!"
        echo ""
        echo "Please update the following in your .env file:"
        echo "  - JWT_SECRET"
        echo "  - REFRESH_TOKEN_SECRET"
        echo "  - MASTER_SECRET_KEY"
        echo ""
        echo "Generate secure secrets with: openssl rand -base64 32"
        exit 1
    fi

    print_success "All critical secrets configured"
}

build_application() {
    print_header "Building Application"

    # SAM build
    print_info "Running SAM build..."
    sam build --use-container

    print_success "Build completed successfully"
}

deploy_application() {
    local ENV=$1

    print_header "Deploying to $ENV Environment"

    # Prepare parameter overrides
    PARAMS="Environment=$ENV"
    PARAMS="$PARAMS JWTSecret=$JWT_SECRET"
    PARAMS="$PARAMS RefreshTokenSecret=$REFRESH_TOKEN_SECRET"
    PARAMS="$PARAMS MasterSecretKey=$MASTER_SECRET_KEY"

    print_info "Deploying with SAM..."

    # Deploy with SAM
    sam deploy \
        --config-env $ENV \
        --parameter-overrides "$PARAMS" \
        --no-fail-on-empty-changeset

    print_success "Deployment completed successfully"
}

show_outputs() {
    local ENV=$1
    local STACK_NAME="basic-auth-$ENV"

    print_header "Deployment Information"

    # Get stack outputs
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")

    FUNCTION_ARN=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`AuthFunctionArn`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")

    echo -e "${GREEN}API Gateway URL:${NC} $API_URL"
    echo -e "${GREEN}Lambda Function:${NC} $FUNCTION_ARN"
    echo ""
    echo -e "${BLUE}Available Endpoints:${NC}"
    echo "  POST   $API_URL/auth/register"
    echo "  POST   $API_URL/auth/register-master"
    echo "  POST   $API_URL/auth/verify"
    echo "  POST   $API_URL/auth/login"
    echo "  POST   $API_URL/auth/refresh"
    echo "  POST   $API_URL/auth/logout"
    echo "  GET    $API_URL/auth/me"
    echo "  PUT    $API_URL/auth/me"
    echo "  GET    $API_URL/users"
    echo "  GET    $API_URL/users/{id}"
    echo "  PUT    $API_URL/users/{id}/role"
    echo "  DELETE $API_URL/users/{id}"
    echo ""
}

show_usage() {
    echo "Usage: $0 [ENVIRONMENT]"
    echo ""
    echo "Environments:"
    echo "  dev      - Development environment (default)"
    echo "  staging  - Staging environment"
    echo "  prod     - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0           # Deploy to dev"
    echo "  $0 dev       # Deploy to dev"
    echo "  $0 staging   # Deploy to staging"
    echo "  $0 prod      # Deploy to prod"
    echo ""
}

# ========================================
# Main Script
# ========================================

# Parse arguments
ENVIRONMENT=${1:-dev}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    show_usage
    exit 1
fi

# Main execution
print_header "Basic Auth API - SAM Deployment"
print_info "Target Environment: $ENVIRONMENT"

check_prerequisites
load_environment $ENVIRONMENT
build_application
deploy_application $ENVIRONMENT
show_outputs $ENVIRONMENT

print_header "Deployment Complete! 🚀"

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Test the API endpoints using the URL above"
echo "2. Create a master user: POST /auth/register-master"
echo "3. Check CloudWatch logs for monitoring"
echo ""
