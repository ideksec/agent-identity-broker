#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Pinned chart versions so the deployment is reproducible and the SBOM can
# name exactly which SPIRE release is running. Bump deliberately.
#   spire 0.30.2 ships SPIRE 1.15.3 (chart appVersion).
SPIRE_CRDS_CHART_VERSION="${SPIRE_CRDS_CHART_VERSION:-0.6.1}"
SPIRE_CHART_VERSION="${SPIRE_CHART_VERSION:-0.30.2}"

helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/ 2>/dev/null || true
helm repo update spiffe

if ! helm -n spire status spire-crds >/dev/null 2>&1; then
  helm install spire-crds spiffe/spire-crds -n spire --create-namespace \
    --version "$SPIRE_CRDS_CHART_VERSION"
fi

# Use upgrade --install so re-runs are idempotent.
helm upgrade --install spire spiffe/spire \
  -n spire \
  --version "$SPIRE_CHART_VERSION" \
  -f "$ROOT/deploy/helm-values/spire-values.yaml" \
  --wait --timeout 5m
