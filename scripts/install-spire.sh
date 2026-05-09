#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/ 2>/dev/null || true
helm repo update spiffe

if ! helm -n spire status spire-crds >/dev/null 2>&1; then
  helm install spire-crds spiffe/spire-crds -n spire --create-namespace
fi

# Use upgrade --install so re-runs are idempotent.
helm upgrade --install spire spiffe/spire \
  -n spire \
  -f "$ROOT/deploy/helm-values/spire-values.yaml" \
  --wait --timeout 5m
