SHELL := /bin/bash
ROOT  := $(shell pwd)
CLUSTER ?= broker
NS_BROKER := broker-system
NS_AGENTS := agents

.PHONY: help up down seed demo logs-broker logs-mock-idp logs-demo \
    psql opa-shell lint test test-unit test-integration \
    images broker-dev mock-idp-dev demo-agent-dev clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

# ------------------------------------------------------------------
# Cluster lifecycle
# ------------------------------------------------------------------
up: ## Create kind cluster, install SPIRE, build images, apply manifests
	@bash scripts/kind-up.sh
	@kubectl --context kind-$(CLUSTER) apply -f deploy/k8s/00-namespaces.yaml
	@bash scripts/install-spire.sh
	@kubectl apply -f deploy/k8s/20-postgres.yaml
	@$(MAKE) images
	@kubectl apply -f deploy/k8s/25-mock-idp.yaml
	@kubectl apply -f deploy/k8s/30-opa-configmap.yaml
	@$(MAKE) seed-secrets
	@kubectl -n $(NS_BROKER) wait --for=condition=ready pod -l app=postgres --timeout=180s
	@kubectl apply -f deploy/k8s/40-broker.yaml
	@kubectl -n $(NS_BROKER) wait --for=condition=available deploy/broker --timeout=180s
	@kubectl -n $(NS_BROKER) wait --for=condition=available deploy/mock-idp --timeout=120s
	@echo "==> cluster ready. run 'make seed' then 'make demo'."

down: ## Delete the kind cluster
	@bash scripts/kind-down.sh

seed: seed-secrets seed-agents ## Seed cluster secrets + agent rows in DB

seed-secrets:
	@bash scripts/setup-secrets.sh

seed-agents:
	@bash scripts/seed-agents.sh

# ------------------------------------------------------------------
# Image build / dev loop
# ------------------------------------------------------------------
images: ## Build and load all docker images into kind
	@bash scripts/load-images.sh

broker-dev: ## Rebuild broker image and rollout-restart
	@docker build -f $(ROOT)/broker/Dockerfile -t localhost/agent-broker/broker:dev $(ROOT)
	@kind load docker-image localhost/agent-broker/broker:dev --name $(CLUSTER)
	@kubectl -n $(NS_BROKER) rollout restart deploy/broker
	@kubectl -n $(NS_BROKER) rollout status deploy/broker

mock-idp-dev: ## Rebuild mock-idp image and rollout-restart
	@docker build -f $(ROOT)/mock-idp/Dockerfile -t localhost/agent-broker/mock-idp:dev $(ROOT)
	@kind load docker-image localhost/agent-broker/mock-idp:dev --name $(CLUSTER)
	@kubectl -n $(NS_BROKER) rollout restart deploy/mock-idp
	@kubectl -n $(NS_BROKER) rollout status deploy/mock-idp

demo-agent-dev: ## Rebuild demo-agent image
	@docker build -f $(ROOT)/demo-agent/Dockerfile -t localhost/agent-broker/demo-agent:dev $(ROOT)
	@kind load docker-image localhost/agent-broker/demo-agent:dev --name $(CLUSTER)

# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------
demo: ## Run the Phase 1 demo Job and tail logs
	@bash scripts/demo.sh

# ------------------------------------------------------------------
# Logs / shells
# ------------------------------------------------------------------
logs-broker: ## Tail broker logs (broker container only)
	@kubectl -n $(NS_BROKER) logs -f deploy/broker -c broker

logs-mock-idp:
	@kubectl -n $(NS_BROKER) logs -f deploy/mock-idp

logs-demo:
	@kubectl -n $(NS_AGENTS) logs -f job/triage-bot-demo

psql: ## Open psql against the broker DB
	@POD=$$(kubectl -n $(NS_BROKER) get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}'); \
	kubectl -n $(NS_BROKER) exec -it $$POD -- psql -U broker -d broker

opa-shell: ## curl loop against the broker's OPA sidecar
	@POD=$$(kubectl -n $(NS_BROKER) get pod -l app=broker -o jsonpath='{.items[0].metadata.name}'); \
	kubectl -n $(NS_BROKER) exec -it $$POD -c opa -- /bin/sh

# ------------------------------------------------------------------
# Lint / tests
# ------------------------------------------------------------------
# All three targets run inside the locked workspace environment (uv.lock) so
# local results match CI. `uv sync --locked --all-packages --all-extras` first.
RUFF_VERSION ?= 0.9.4

lint: ## Run ruff over the whole repo
	@uv run --locked --with "ruff==$(RUFF_VERSION)" ruff check .

test: test-unit ## Run all tests

test-unit: ## Run unit tests (no cluster needed)
	@cd $(ROOT) && uv run --locked python -m pytest tests/unit -v

test-integration: ## Run integration tests against the running cluster
	@cd $(ROOT) && uv run --locked python -m pytest tests/integration -v

# ------------------------------------------------------------------
clean: down ## Tear down everything
	@rm -rf .venv
