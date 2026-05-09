#!/usr/bin/env bash
set -euo pipefail

CLUSTER="${KIND_CLUSTER_NAME:-broker}"
kind delete cluster --name "$CLUSTER"
