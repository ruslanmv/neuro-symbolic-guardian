.PHONY: help install dev test lint format clean docker k8s

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with UV
	uv venv --python 3.11
	. .venv/bin/activate && uv pip install -e .

dev:  ## Install development dependencies
	uv pip install -e ".[dev]"

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=ns_guardian --cov=aegis --cov-report=html --cov-report=term

lint:  ## Run linting
	ruff check .

format:  ## Format code
	ruff format .

typecheck:  ## Run type checking
	mypy src/

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# Docker targets
docker-build:  ## Build Docker image
	docker build -t neuro-symbolic-guardian:latest .

docker-run-mcp:  ## Run Docker container as MCP server
	docker run -it --rm neuro-symbolic-guardian:latest

docker-run-api:  ## Run Docker container as API server
	docker run -p 8000:8000 --rm neuro-symbolic-guardian:latest ns-guardian --mode api

docker-compose-up:  ## Start services with docker-compose
	docker-compose up -d

docker-compose-down:  ## Stop services with docker-compose
	docker-compose down

# Kubernetes targets
k8s-deploy:  ## Deploy to Kubernetes
	kubectl apply -f k8s/deployment.yaml

k8s-delete:  ## Delete from Kubernetes
	kubectl delete namespace neuro-symbolic-guardian

k8s-logs:  ## View Kubernetes logs
	kubectl logs -f deployment/guardian-api -n neuro-symbolic-guardian

k8s-port-forward:  ## Port forward to local
	kubectl port-forward svc/guardian-api 8000:80 -n neuro-symbolic-guardian

# Development server targets
run-mcp:  ## Run as MCP server
	ns-guardian --mode mcp

run-api:  ## Run as API server
	ns-guardian --mode api --host 0.0.0.0 --port 8000

run-cli:  ## Run example CLI command
	ns-guardian --mode cli --text "consume 3 from 2" --facts '{"inventory": 2}'

# Policy management
policy-validate:  ## Validate policy files
	python -c "from aegis.policy import load_policy; load_policy('policies/production.yaml'); print('Policy valid')"

# Release targets
bump-version:  ## Bump version (use VERSION=x.y.z)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump-version VERSION=x.y.z"; exit 1; fi
	sed -i 's/version = ".*"/version = "$(VERSION)"/' pyproject.toml
	sed -i 's/version: ".*"/version: "$(VERSION)"/' policies/production.yaml
	@echo "Version bumped to $(VERSION)"

release:  ## Create a release (requires VERSION)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=x.y.z"; exit 1; fi
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)
	@echo "Release v$(VERSION) created"
