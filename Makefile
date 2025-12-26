.PHONY: help install build deploy deploy-dev deploy-staging deploy-prod validate test clean logs destroy local-api local-invoke package

# Default environment
ENV ?= dev

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)Basic Auth API - Makefile Commands$(NC)'
	@echo ''
	@echo 'Usage:'
	@echo '  make [target] [ENV=environment]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ''
	@echo 'Examples:'
	@echo '  make deploy                # Deploy to dev (default)'
	@echo '  make deploy ENV=staging    # Deploy to staging'
	@echo '  make logs ENV=prod         # View prod logs'

install: ## Install Python dependencies locally
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

validate: ## Validate SAM template
	@echo "$(BLUE)Validating SAM template...$(NC)"
	sam validate --lint
	@echo "$(GREEN)✓ Template is valid$(NC)"

build: ## Build the SAM application
	@echo "$(BLUE)Building application...$(NC)"
	sam build --use-container
	@echo "$(GREEN)✓ Build completed$(NC)"

package: build ## Package application for deployment
	@echo "$(BLUE)Packaging application...$(NC)"
	sam package --output-template-file packaged.yaml
	@echo "$(GREEN)✓ Package created$(NC)"

deploy: ## Deploy to default environment (dev)
	@echo "$(BLUE)Deploying to $(ENV) environment...$(NC)"
	./deploy-sam.sh $(ENV)
	@echo "$(GREEN)✓ Deployment completed$(NC)"

deploy-dev: ## Deploy to dev environment
	@$(MAKE) deploy ENV=dev

deploy-staging: ## Deploy to staging environment
	@$(MAKE) deploy ENV=staging

deploy-prod: ## Deploy to production environment
	@$(MAKE) deploy ENV=prod

local-api: ## Run API locally using SAM
	@echo "$(BLUE)Starting local API...$(NC)"
	@echo "$(YELLOW)API will be available at: http://127.0.0.1:3000$(NC)"
	sam local start-api --env-vars .env

local-invoke: ## Invoke Lambda function locally
	@echo "$(BLUE)Invoking function locally...$(NC)"
	@if [ ! -f events/test-event.json ]; then \
		echo "$(YELLOW)Creating test event...$(NC)"; \
		mkdir -p events; \
		echo '{"httpMethod": "POST", "path": "/auth/login", "body": "{\"email\":\"test@example.com\",\"password\":\"password123\"}"}' > events/test-event.json; \
	fi
	sam local invoke AuthFunction --event events/test-event.json

logs: ## Tail Lambda function logs
	@echo "$(BLUE)Tailing logs for $(ENV) environment...$(NC)"
	@FUNCTION_NAME=$$(aws cloudformation describe-stacks \
		--stack-name basic-auth-$(ENV) \
		--query 'Stacks[0].Outputs[?OutputKey==`AuthFunctionArn`].OutputValue' \
		--output text 2>/dev/null | awk -F: '{print $$NF}') && \
	if [ -n "$$FUNCTION_NAME" ]; then \
		sam logs -n $$FUNCTION_NAME --stack-name basic-auth-$(ENV) --tail; \
	else \
		echo "$(YELLOW)Stack not found. Have you deployed yet?$(NC)"; \
	fi

test: ## Run tests (placeholder)
	@echo "$(BLUE)Running tests...$(NC)"
	@echo "$(YELLOW)No tests configured yet. Add tests in tests/ directory.$(NC)"

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf .aws-sam
	rm -rf package
	rm -f packaged.yaml
	rm -f lambda-deployment.zip
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

describe: ## Show stack outputs
	@echo "$(BLUE)Stack outputs for $(ENV) environment:$(NC)"
	@aws cloudformation describe-stacks \
		--stack-name basic-auth-$(ENV) \
		--query 'Stacks[0].Outputs' \
		--output table 2>/dev/null || echo "$(YELLOW)Stack not found$(NC)"

destroy: ## Destroy stack (⚠️  WARNING: Deletes all resources!)
	@echo "$(YELLOW)⚠️  WARNING: This will delete all resources in $(ENV) environment!$(NC)"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(BLUE)Deleting stack...$(NC)"; \
		sam delete --stack-name basic-auth-$(ENV) --no-prompts; \
		echo "$(GREEN)✓ Stack deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

status: ## Show deployment status
	@echo "$(BLUE)Deployment status for $(ENV) environment:$(NC)"
	@aws cloudformation describe-stacks \
		--stack-name basic-auth-$(ENV) \
		--query 'Stacks[0].{Status:StackStatus,LastUpdated:LastUpdatedTime}' \
		--output table 2>/dev/null || echo "$(YELLOW)Stack not found$(NC)"

endpoints: ## Show API endpoints
	@echo "$(BLUE)API endpoints for $(ENV) environment:$(NC)"
	@API_URL=$$(aws cloudformation describe-stacks \
		--stack-name basic-auth-$(ENV) \
		--query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
		--output text 2>/dev/null); \
	if [ -n "$$API_URL" ]; then \
		echo ""; \
		echo "$(GREEN)Base URL:$(NC) $$API_URL"; \
		echo ""; \
		echo "$(BLUE)Available endpoints:$(NC)"; \
		echo "  POST   $${API_URL}auth/register"; \
		echo "  POST   $${API_URL}auth/register-master"; \
		echo "  POST   $${API_URL}auth/verify"; \
		echo "  POST   $${API_URL}auth/login"; \
		echo "  POST   $${API_URL}auth/refresh"; \
		echo "  POST   $${API_URL}auth/logout"; \
		echo "  GET    $${API_URL}auth/me"; \
		echo "  PUT    $${API_URL}auth/me"; \
		echo "  GET    $${API_URL}users"; \
		echo "  GET    $${API_URL}users/{id}"; \
		echo "  PUT    $${API_URL}users/{id}/role"; \
		echo "  DELETE $${API_URL}users/{id}"; \
		echo ""; \
	else \
		echo "$(YELLOW)Stack not found. Have you deployed yet?$(NC)"; \
	fi

env-setup: ## Set up .env file from example
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env file created$(NC)"; \
		echo "$(YELLOW)⚠️  Please edit .env and update the secrets!$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

generate-secrets: ## Generate random secrets for .env
	@echo "$(BLUE)Generating secure secrets...$(NC)"
	@echo ""
	@echo "$(GREEN)Add these to your .env file:$(NC)"
	@echo ""
	@echo "JWT_SECRET=$$(openssl rand -base64 32)"
	@echo "REFRESH_TOKEN_SECRET=$$(openssl rand -base64 32)"
	@echo "MASTER_SECRET_KEY=$$(openssl rand -base64 32)"
	@echo ""

quick-deploy: build deploy ## Quick build and deploy (use with caution)

all: validate build deploy ## Run full pipeline: validate, build, deploy

.DEFAULT_GOAL := help
