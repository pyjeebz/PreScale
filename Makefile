# Prescale - Makefile for common operations
# Run 'make help' to see available commands

.PHONY: help install dev up down build test clean lint

# Default target
help:
	@echo "Prescale Development Commands"
	@echo "============================"
	@echo ""
	@echo "Local Development:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make dev         - Start inference service locally (no Docker)"
	@echo "  make up          - Start all services with Docker Compose"
	@echo "  make down        - Stop Docker Compose services"
	@echo "  make build       - Build Docker images"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-api    - Test API endpoints"
	@echo "  make lint        - Run linters"
	@echo ""
	@echo "Kubernetes:"
	@echo "  make k8s-apply   - Apply Kubernetes manifests"
	@echo "  make k8s-delete  - Delete Kubernetes resources"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make agent       - Run Prescale agent locally"

# ============================================================================
# Local Development
# ============================================================================

install:
	python -m pip install --upgrade pip
	pip install -e ./agent[dev]
	pip install -r ml/inference/requirements.txt

dev:
	cd ml && python -m uvicorn inference.app:app --host 0.0.0.0 --port 8080 --reload

agent:
	cd agent && python -m prescale_agent run --config ../prescale-agent.yaml

# ============================================================================
# Docker Compose
# ============================================================================

up:
	docker compose up -d inference

up-all:
	docker compose --profile monitoring up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f inference

# ============================================================================
# Testing
# ============================================================================

test:
	pytest ml/tests/ agent/tests/ -v

test-api:
	@echo "Testing health endpoint..."
	curl -s http://localhost:8080/health | python -m json.tool
	@echo ""
	@echo "Testing ready endpoint..."
	curl -s http://localhost:8080/ready | python -m json.tool
	@echo ""
	@echo "Testing predict endpoint..."
	curl -s -X POST http://localhost:8080/predict \
		-H "Content-Type: application/json" \
		-d '{"deployment": "test", "namespace": "default", "metric": "cpu_utilization"}' | python -m json.tool

lint:
	ruff check ml/ agent/
	ruff format --check ml/ agent/

format:
	ruff format ml/ agent/

# ============================================================================
# Kubernetes
# ============================================================================

k8s-apply:
	kubectl apply -f infra/kubernetes/prescale-inference/

k8s-delete:
	kubectl delete -f infra/kubernetes/prescale-inference/

k8s-logs:
	kubectl logs -n prescale -l app.kubernetes.io/name=prescale-inference -f

k8s-status:
	kubectl get pods,svc,deploy -n prescale

# ============================================================================
# Cleanup
# ============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .ruff_cache build dist
