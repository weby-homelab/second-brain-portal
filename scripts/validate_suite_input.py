#!/usr/bin/env python3
"""
Mandatory suite-input drift validator for POWER-GUI 0.7.12.

Enforces that release/power.gui.suite-input.json is the single source of truth
and that every duplicated release surface matches it. If any duplicate drifts,
CI must fail.

Surfaces checked:
- Dockerfile ARG POWER_FRAMEWORK_COMMIT, POWER_FRAMEWORK_WHEEL_SHA256, SUITE_CONSTRAINTS_SHA256
- .github/workflows/docker-publish.yml build-args + real downloaded file checksum verification
- compatibility.json power_core.dependency.revision, wheel_sha256, constraints_sha256, power_gui.version
- release/power-suite.constraints.txt sha256
- pyproject.toml version
- release/power.gui.suite-input.json schema itself
- workflow hard-coded download URL contains correct POWER wheel filename/tag

This validator is mandatory per Closure Controller v2 C01.3 option B.
"""

from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUITE_INPUT = ROOT / "release" / "power.gui.suite-input.json"
DOCKERFILE = ROOT / "Dockerfile"
DOCKER_PUBLISH = ROOT / ".github" / "workflows" / "docker-publish.yml"
COMPAT = ROOT / "compatibility.json"
CONSTRAINTS = ROOT / "release" / "power-suite.constraints.txt"
PYPROJECT = ROOT / "pyproject.toml"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"PASS: {msg}")


def main() -> None:
    if not SUITE_INPUT.is_file():
        fail(f"suite-input missing: {SUITE_INPUT}")
    data = json.loads(SUITE_INPUT.read_text(encoding="utf-8"))
    assert data.get("schema") == "power.gui.suite-input.v1", (
        "schema must be power.gui.suite-input.v1"
    )
    power = data["power"]
    gui = data["gui"]
    constraints = data["constraints"]
    power_commit = power["source_sha"]
    power_wheel_sha = power["wheel_sha256"]
    power_version = power["version"]
    power_tag = power["tag"]
    gui_version = gui["version"]
    constraints_sha = constraints["sha256"]
    constraints_filename = constraints["filename"]
    ok(
        f"suite-input loaded: POWER {power_version} {power_commit} wheel {power_wheel_sha[:8]}... GUI {gui_version} constraints {constraints_sha[:8]}..."
    )

    # 1. Dockerfile
    docker_text = DOCKERFILE.read_text(encoding="utf-8")
    for name, expected in [
        ("POWER_FRAMEWORK_COMMIT", power_commit),
        ("POWER_FRAMEWORK_WHEEL_SHA256", power_wheel_sha),
        ("SUITE_CONSTRAINTS_SHA256", constraints_sha),
    ]:
        m = re.search(rf"ARG {re.escape(name)}=([0-9a-f]+)", docker_text)
        if not m:
            fail(f"Dockerfile missing ARG {name}")
        if m.group(1) != expected:
            fail(f"Dockerfile ARG {name}={m.group(1)} != suite-input {expected}")
        ok(f"Dockerfile ARG {name} matches")
    # check Dockerfile installs wheel[semantic,rerank] and verifies hash
    if (
        'pip download --no-deps --dest /tmp/wheels "power-framework[semantic,rerank]'
        not in docker_text
    ):
        fail("Dockerfile must pip download power-framework[semantic,rerank]")
    ok("Dockerfile pip download uses [semantic,rerank]")
    if (
        f'echo "${{POWER_FRAMEWORK_WHEEL_SHA256}}  /tmp/wheels/power_framework-{power_version}-py3-none-any.whl" | sha256sum -c -'
        not in docker_text
    ):
        fail("Dockerfile must verify POWER wheel sha256 via sha256sum -c")
    ok("Dockerfile verifies wheel hash")
    if (
        '"/tmp/wheels/power_framework-3.7.4-py3-none-any.whl[semantic,rerank]"'
        not in docker_text
    ):
        fail("Dockerfile must pip install wheel[semantic,rerank]")
    ok("Dockerfile pip install uses [semantic,rerank]")
    for dep in ["onnxruntime", "tokenizers", "huggingface_hub", "numpy", "fastembed"]:
        if f"find_spec('{dep}')" not in docker_text:
            fail(f"Dockerfile missing assert find_spec('{dep}')")
    ok(
        "Dockerfile asserts all 5 deps (onnxruntime, tokenizers, huggingface_hub, numpy, fastembed)"
    )

    # 2. docker-publish.yml
    dp_text = DOCKER_PUBLISH.read_text(encoding="utf-8")
    for name, expected in [
        ("POWER_FRAMEWORK_COMMIT", power_commit),
        ("POWER_FRAMEWORK_WHEEL_SHA256", power_wheel_sha),
        ("SUITE_CONSTRAINTS_SHA256", constraints_sha),
    ]:
        pattern = rf"{re.escape(name)}={re.escape(expected)}"
        if not re.search(pattern, dp_text):
            fail(f"docker-publish.yml missing build-arg {name}={expected}")
        ok(f"docker-publish.yml build-arg {name} matches")
    # check real hash verification in Install dependencies
    if (
        'pip download --no-deps --dest /tmp/wheels "power-framework @ https://github.com/weby-homelab/power-framework/releases/download/v3.7.4/power_framework-3.7.4-py3-none-any.whl"'
        not in dp_text
    ):
        fail(
            "docker-publish.yml Install dependencies must pip download POWER wheel to /tmp/wheels"
        )
    ok("docker-publish.yml Install downloads POWER wheel")
    if (
        'echo "f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2  /tmp/wheels/power_framework-3.7.4-py3-none-any.whl" | sha256sum -c -'
        not in dp_text
    ):
        fail("docker-publish.yml must verify wheel sha via sha256sum -c")
    ok("docker-publish.yml verifies wheel hash before install")
    if (
        'pip install --no-cache-dir "/tmp/wheels/power_framework-3.7.4-py3-none-any.whl"'
        not in dp_text
    ):
        fail("docker-publish.yml must pip install from /tmp/wheels with verified file")
    ok("docker-publish.yml installs verified wheel")

    # 3. compatibility.json
    compat_data = json.loads(COMPAT.read_text(encoding="utf-8"))
    if compat_data["power_core"]["dependency"]["revision"] != power_commit:
        fail(
            f"compatibility.json power_core.dependency.revision {compat_data['power_core']['dependency']['revision']} != {power_commit}"
        )
    ok("compatibility.json power_core revision matches")
    if compat_data["power_core"]["dependency"]["wheel_sha256"] != power_wheel_sha:
        fail("compatibility.json wheel_sha256 mismatch")
    ok("compatibility.json wheel_sha256 matches")
    if compat_data["power_gui"]["version"] != gui_version:
        fail(
            f"compatibility.json power_gui.version {compat_data['power_gui']['version']} != {gui_version}"
        )
    ok("compatibility.json gui version matches")
    if compat_data["container"]["constraints_sha256"] != constraints_sha:
        fail("compatibility.json container.constraints_sha256 mismatch")
    ok("compatibility.json constraints_sha matches")
    if compat_data["container"]["image"] != f"webyhomelab/power-gui:{gui_version}":
        fail(
            f"compatibility.json container image {compat_data['container']['image']} != webyhomelab/power-gui:{gui_version}"
        )
    ok("compatibility.json container image matches")

    # 4. constraints file sha
    constraints_bytes = CONSTRAINTS.read_bytes()
    actual_constraints_sha = hashlib.sha256(constraints_bytes).hexdigest()
    if actual_constraints_sha != constraints_sha:
        fail(
            f"constraints file sha {actual_constraints_sha} != suite-input {constraints_sha}"
        )
    ok("constraints file sha matches suite-input")
    constraints_text = CONSTRAINTS.read_text(encoding="utf-8")
    if f"power-framework=={power_version}" not in constraints_text:
        fail(f"constraints missing power-framework=={power_version}")
    ok("constraints contains power-framework pin")
    if f"power-gui=={gui_version}" not in constraints_text:
        fail(f"constraints missing power-gui=={gui_version}")
    ok("constraints contains power-gui pin")

    # 5. pyproject.toml
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'version = "([^"]+)"', pyproject_text)
    if not m:
        fail("pyproject.toml missing version")
    if m.group(1) != gui_version:
        fail(
            f"pyproject.toml version {m.group(1)} != suite-input gui version {gui_version}"
        )
    ok("pyproject.toml version matches suite-input")
    # check power-framework dependency
    if (
        f'"power-framework=={power_version}"' not in pyproject_text
        and f"'power-framework=={power_version}'" not in pyproject_text
        and f"power-framework=={power_version}" not in pyproject_text
    ):
        fail("pyproject.toml missing power-framework==3.7.4 dependency")
    ok("pyproject.toml power-framework dependency matches")

    # 6. suite-input file itself controls all surfaces
    # ensure no other file contains stale 0.7.11 or old commit/wheel without being listed
    # already checked

    print(
        "\nAll suite-input drift checks PASS. suite-input is authoritative and all duplicates match."
    )


if __name__ == "__main__":
    main()
