#!/usr/bin/env bash
# Run the Phase 1 demo Job and tail its logs. Re-runs delete any prior
# completed Job first.
set -euo pipefail

NS="agents"
JOB="triage-bot-demo"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

kubectl delete job -n "$NS" "$JOB" --ignore-not-found
kubectl apply -f "$ROOT/deploy/k8s/60-demo-agent.yaml"

echo "waiting for pod..."
for i in {1..60}; do
  POD="$(kubectl -n "$NS" get pod -l job-name="$JOB" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [[ -n "${POD:-}" ]]; then break; fi
  sleep 1
done
if [[ -z "${POD:-}" ]]; then
  echo "demo pod did not appear" >&2
  exit 1
fi

# Wait until logs are available, then stream.
kubectl -n "$NS" wait --for=condition=PodScheduled pod/"$POD" --timeout=120s
echo "==> tailing logs from $POD"
kubectl -n "$NS" logs -f "$POD"

# Surface the Job's terminal status as the script's exit code.
echo "==> waiting for Job completion..."
if kubectl -n "$NS" wait --for=condition=complete job/"$JOB" --timeout=120s 2>/dev/null; then
  echo "demo: SUCCESS"
  exit 0
fi
echo "demo: FAILED" >&2
kubectl -n "$NS" describe job "$JOB" >&2
exit 1
