#!/usr/bin/env python3
"""Emit a CycloneDX 1.6 deployment BOM from what the repo actually deploys.

Application code is covered by the per-image SBOMs that Syft generates in CI.
This script covers the layer those miss: the third-party container images the
Kubernetes manifests pull, the base and build-stage images the Dockerfiles use,
and the pinned Helm charts. Everything is read from the manifests themselves,
so the BOM cannot drift from the deployment without a diff.

    python3 scripts/deployment-bom.py -o sbom/deployment.cdx.json
    python3 scripts/deployment-bom.py --list-images   # third-party images only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL_IMAGE_PREFIX = "localhost/agent-broker/"


def _version() -> str:
    init = (ROOT / "broker" / "src" / "broker" / "__init__.py").read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    return m.group(1) if m else "0.0.0"


def deployed_images() -> list[str]:
    """Third-party images referenced by deploy/k8s/*.yaml (in file order)."""
    seen: list[str] = []
    for path in sorted((ROOT / "deploy" / "k8s").glob("*.yaml")):
        for m in re.finditer(r'^\s*image:\s*["\']?([^"\'\s]+)', path.read_text(), re.M):
            img = m.group(1)
            if img.startswith(LOCAL_IMAGE_PREFIX) or img in seen:
                continue
            seen.append(img)
    return seen


def dockerfile_images() -> list[tuple[str, list[str]]]:
    """(image, roles) for every external image a Dockerfile pulls.

    One entry per image ref; an image used both as a build stage and as the
    runtime base (python:3.12-slim) gets both roles rather than two entries,
    because CycloneDX bom-refs must be unique.
    """
    roles: dict[str, list[str]] = {}

    def add(img: str, role: str) -> None:
        roles.setdefault(img, [])
        if role not in roles[img]:
            roles[img].append(role)

    for df in sorted(ROOT.glob("*/Dockerfile")):
        text = df.read_text()
        stages = set(re.findall(r"^FROM\s+\S+\s+AS\s+(\S+)", text, re.M | re.I))
        for m in re.finditer(r"^FROM\s+(\S+)(\s+AS\s+\S+)?", text, re.M | re.I):
            img, as_stage = m.group(1), m.group(2)
            if img in stages:
                continue
            add(img, "build-stage" if as_stage else "base-image")
        for m in re.finditer(r"^COPY\s+--from=(\S+)", text, re.M):
            if m.group(1) not in stages:
                add(m.group(1), "build-stage")
    return list(roles.items())


def helm_charts() -> list[tuple[str, str, str]]:
    """(chart, version, repo) pinned in scripts/install-spire.sh."""
    text = (ROOT / "scripts" / "install-spire.sh").read_text()
    repo = re.search(r"helm repo add \S+ (\S+)", text)
    repo_url = repo.group(1) if repo else ""
    charts = []
    for name, var in (("spire-crds", "SPIRE_CRDS_CHART_VERSION"), ("spire", "SPIRE_CHART_VERSION")):
        m = re.search(rf'{var}="\$\{{{var}:-([^}}]+)\}}"', text)
        if m:
            charts.append((name, m.group(1), repo_url))
    return charts


def _split_image(ref: str) -> tuple[str, str, str]:
    """'ghcr.io/astral-sh/uv:0.8.17' -> (registry, 'astral-sh/uv', '0.8.17')."""
    registry = ""
    rest = ref
    first = ref.split("/", 1)[0]
    if "/" in ref and ("." in first or ":" in first or first == "localhost"):
        registry, rest = ref.split("/", 1)
    if "@" in rest:
        name, tag = rest.split("@", 1)
    elif ":" in rest:
        name, tag = rest.rsplit(":", 1)
    else:
        name, tag = rest, "latest"
    return registry, name, tag


def _container(ref: str, roles: list[str]) -> dict:
    registry, name, tag = _split_image(ref)
    purl = f"pkg:docker/{name}@{tag}"
    if registry:
        purl += f"?repository_url={registry}"
    return {
        "type": "container",
        "bom-ref": f"container:{ref}",
        "name": name,
        "version": tag,
        "purl": purl,
        "properties": [
            *({"name": "broker:role", "value": r} for r in roles),
            {"name": "broker:image-ref", "value": ref},
        ],
    }


def _chart(name: str, version: str, repo: str) -> dict:
    purl = f"pkg:generic/helm/{name}@{version}"
    if repo:
        purl += f"?download_url={repo}"
    return {
        "type": "application",
        "bom-ref": f"helm:{name}@{version}",
        "name": f"helm chart {name}",
        "version": version,
        "purl": purl,
        "properties": [
            {"name": "broker:role", "value": "deployed-chart"},
            {"name": "broker:helm-repo", "value": repo},
        ],
    }


def build_bom() -> dict:
    by_ref: dict[str, list[str]] = {i: ["deployed-image"] for i in deployed_images()}
    for img, roles in dockerfile_images():
        by_ref.setdefault(img, [])
        by_ref[img] += [r for r in roles if r not in by_ref[img]]
    components = [_container(i, r) for i, r in by_ref.items()]
    components += [_chart(*c) for c in helm_charts()]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "tools": {
                "components": [
                    {"type": "application", "name": "deployment-bom.py", "version": _version()}
                ]
            },
            "component": {
                "type": "application",
                "bom-ref": "agent-identity-broker",
                "name": "agent-identity-broker",
                "version": _version(),
                "description": (
                    "Deployment BOM: third-party images, base images and Helm charts "
                    "read from deploy/, */Dockerfile and scripts/."
                ),
            },
        },
        "components": components,
        "dependencies": [
            {"ref": "agent-identity-broker", "dependsOn": [c["bom-ref"] for c in components]},
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--output", type=pathlib.Path, help="write JSON here (default: stdout)")
    ap.add_argument(
        "--list-images", action="store_true", help="print third-party deployed images, one per line"
    )
    args = ap.parse_args(argv)

    if args.list_images:
        print("\n".join(deployed_images()))
        return 0

    bom = json.dumps(build_bom(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(bom)
        print(f"wrote {args.output} ({len(build_bom()['components'])} components)", file=sys.stderr)
    else:
        sys.stdout.write(bom)
    return 0


if __name__ == "__main__":
    sys.exit(main())
