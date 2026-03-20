# =============================================================================
# OwnBot Makefile
#
# Provides convenient shortcuts for common development tasks.
# =============================================================================

.PHONY: help install install-dev test test-unit test-integration lint format type-check clean coverage docs build upload

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3
PIP := pip3

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "OwnBot Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Installation
# =============================================================================

install: ## Install the package
	$(PIP) install -e .

install-dev: ## Install the package with development dependencies
	$(PIP) install -e ".[dev]"
	pre-commit install

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit -v -m "not slow"

test-integration: ## Run integration tests
	pytest tests/integration -v -m "integration"

test-fast: ## Run tests in fast mode (skip slow tests)
	pytest tests/unit -v -m "not slow and not integration"

test-parallel: ## Run tests in parallel
	pytest tests/unit -v -n auto

coverage: ## Run tests with coverage report
	pytest tests/unit --cov=ownbot --cov-report=term --cov-report=html

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linter (ruff)
	ruff check ownbot tests

lint-fix: ## Run linter with auto-fix
	ruff check --fix ownbot tests

format: ## Format code with ruff
	ruff format ownbot tests

format-check: ## Check code formatting
	ruff format --check ownbot tests

type-check: ## Run type checker (mypy)
	mypy ownbot

type-check-strict: ## Run type checker in strict mode
	mypy ownbot --strict

# =============================================================================
# Pre-commit
# =============================================================================

pre-commit: ## Run all pre-commit hooks
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# =============================================================================
# Security
# =============================================================================

security: ## Run security scan (bandit)
	bandit -r ownbot -f json -o bandit-report.json || true

security-check: ## Run security scan (verbose)
	bandit -r ownbot -ll

# =============================================================================
# Building & Distribution
# =============================================================================

build: ## Build the package
	$(PYTHON) -m build

check: ## Check the package with twine
	twine check dist/*

upload-test: ## Upload to TestPyPI
	twine upload --repository testpypi dist/*

upload: ## Upload to PyPI
	twine upload dist/*

# =============================================================================
# Cleaning
# =============================================================================

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .eggs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	rm -f bandit-report.json

clean-all: clean ## Clean everything including virtual environments
	rm -rf venv/
	rm -rf .venv/
	rm -rf env/

# =============================================================================
# Development
# =============================================================================

run: ## Run the bot (requires configuration)
	ownbot gateway

onboard: ## Run the onboarding command
	ownbot onboard

shell: ## Start a Python shell with the package loaded
	$(PYTHON) -c "import ownbot; print('OwnBot', ownbot.__version__, 'loaded')" && $(PYTHON) -i -c "from ownbot import *"

# =============================================================================
# Documentation
# =============================================================================

docs: ## Generate documentation (if configured)
	@echo "Documentation generation not yet configured"

# =============================================================================
# Utilities
# =============================================================================

update-deps: ## Update dependencies
	$(PIP) install --upgrade -e ".[dev]"

pip-list: ## List installed packages
	$(PIP) list

pip-freeze: ## Freeze dependencies
	$(PIP) freeze > requirements.txt
