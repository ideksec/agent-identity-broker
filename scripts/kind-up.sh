#!/usr/bin/env bash
set -euo pipefail

CLUSTER="${KIND_CLUSTER_NAME:-broker}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if kind get clusters | grep -qx "$CLUSTER"; then
  echo "kind cluster '$CLUSTER' already exists"
else
  echo "creating kind cluster '$CLUSTER'..."
  kind create cluster --name "$CLUSTER" --config "$ROOT/deploy/kind-config.yaml"
fi

kubectl --context "kind-$CLUSTER" cluster-info
