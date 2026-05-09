#!/usr/bin/env bash
# Generate per-cluster secrets used by Phase 1: postgres password, vault key,
# and a stable RSA keypair for the mock IdP. Idempotent — keeps existing
# values if the secret already exists.
set -euo pipefail

NS="broker-system"

ensure_secret_literal() {
  local name="$1"; local key="$2"; local value="$3"
  if kubectl -n "$NS" get secret "$name" >/dev/null 2>&1; then
    echo "secret/${name} exists"
  else
    kubectl -n "$NS" create secret generic "$name" --from-literal="${key}=${value}"
  fi
}

ensure_secret_files() {
  local name="$1"; shift
  if kubectl -n "$NS" get secret "$name" >/dev/null 2>&1; then
    echo "secret/${name} exists"
    return
  fi
  kubectl -n "$NS" create secret generic "$name" "$@"
}

# Postgres password.
PG_PW="${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}"
ensure_secret_literal postgres password "$PG_PW"

# Vault key (32 bytes base64).
VAULT_KEY="$(openssl rand -base64 32)"
ensure_secret_literal vault-key key "$VAULT_KEY"

# Mock IdP stable RSA keypair.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
openssl genrsa -out "$TMP/private_key" 2048 >/dev/null 2>&1
openssl rsa -in "$TMP/private_key" -pubout -out "$TMP/public_key" >/dev/null 2>&1
ensure_secret_files mock-idp-key \
  --from-file=private_key="$TMP/private_key" \
  --from-file=public_key="$TMP/public_key"

# Broker federation key (Phase 3+ but generate now so it's ready).
openssl genrsa -out "$TMP/fed_private_key" 2048 >/dev/null 2>&1
openssl rsa -in "$TMP/fed_private_key" -pubout -out "$TMP/fed_public_key" >/dev/null 2>&1
ensure_secret_files broker-fed-key \
  --from-file=private_key="$TMP/fed_private_key" \
  --from-file=public_key="$TMP/fed_public_key"

echo "secrets ready in namespace ${NS}"
