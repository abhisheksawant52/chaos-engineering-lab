.DEFAULT_GOAL := help
.PHONY: help install lint format test build clean run docker-build validate-manifests

IMAGE ?= ghcr.io/abhisheksawant52/chaos-engineering-lab:0.1.0

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

lint: ## Run ruff and black in check mode
	ruff check src tests
	black --check src tests

format: ## Auto-format the codebase
	ruff check --fix src tests
	black src tests

test: ## Run the test suite
	pytest

run: ## List discovered experiments (EXPERIMENT=<name> to run one)
	@if [ -n "$(EXPERIMENT)" ]; then chaos-lab run $(EXPERIMENT); else chaos-lab list; fi

build: ## Build distribution artifacts
	python -m pip install --upgrade build
	python -m build

docker-build: ## Build the container image
	docker build -t $(IMAGE) .

validate-manifests: ## Validate experiment manifests (best-effort, non-failing)
	chaos-lab validate || true
	@command -v kubectl >/dev/null 2>&1 && \
		for f in experiments/litmus/*.yaml experiments/chaos-mesh/*.yaml; do \
			kubectl apply --dry-run=client -f "$$f" || true; \
		done || echo "kubectl not found; skipped cluster-side dry-run."

clean: ## Remove build and cache artifacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
