#!/usr/bin/env bash
set -euo pipefail

CLUSTER="${KIND_CLUSTER_NAME:-broker}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

build_and_load() {
  local name="$1"
  local dockerfile="$2"
  local context="$3"
  local image="localhost/agent-broker/${name}:dev"

  echo "==> building ${image}"
  docker build -f "$dockerfile" -t "$image" "$context"
  echo "==> loading ${image} into kind cluster '$CLUSTER'"
  kind load docker-image "$image" --name "$CLUSTER"
}

build_and_load broker "$ROOT/broker/Dockerfile" "$ROOT"
build_and_load mock-idp "$ROOT/mock-idp/Dockerfile" "$ROOT"
build_and_load demo-agent "$ROOT/demo-agent/Dockerfile" "$ROOT"
