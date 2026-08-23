#!/usr/bin/env python3
"""
Mandatory suite-input drift validator for POWER-GUI 0.7.12.

Enforces that release/power.gui.suite-input.json is the single source of truth
and that every duplicated release surface matches it. If any duplicate drifts,
CI must fail.

Surfaces checked (v4 mandatory, explicit allowlist, historical evidence excluded):
- Dockerfile (ARG POWER_FRAMEWORK_COMMIT, POWER_FRAMEWORK_WHEEL_SHA256, SUITE_CONSTRAINTS_SHA256, [semantic,rerank] install, 5 asserts, sha256sum -c)
- .github/workflows/docker-publish.yml (build-args POWER_FRAMEWORK_COMMIT, POWER_FRAMEWORK_WHEEL_SHA256, SUITE_CONSTRAINTS_SHA256, real pip download + sha256sum -c, Validate suite-input drift step)
- .github/workflows/release.yml (version-agnostic, expected from GITHUB_REF_NAME, no hard-coded 0.7.10)
- compatibility.json (power_core.dependency.revision, wheel_sha256, constraints_sha256, power_gui.version, power_core.candidate_revision null, verification 0.7.12, version_strategy [semantic,rerank])
- release/power-suite.constraints.txt (sha256, power-framework==3.7.4, power-gui==0.7.12)
- release/power.gui.suite-input.json (schema power.gui.suite-input.v1, no generated_at_utc, power 3.7.4, gui 0.7.12, constraints sha)
- release/release-<gui-version>.md (0.7.12, Semantic + Rerank, Sxx wording, no Murge typo, no future digest claim)
- pyproject.toml (version 0.7.12, power-framework==3.7.4, Requires-Python >=3.13,<3.15)
- src/power_gui/__init__.py (__version__ 0.7.12)
- uv.lock (power-gui 0.7.12, power-framework rev 13dd835)
- README.md (GUI 0.7.12 candidate, POWER 3.7.4, webyhomelab/power-gui:0.7.12, softwareVersion 0.7.12, publication pending)
- README.ua.md (same)
- docker-compose.yml (image webyhomelab/power-gui:0.7.12, cap_drop ALL, no NET_ADMIN/NET_RAW, read_only, non-root)
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

    # suite-input should not contain generated_at_utc (FND-06)
    if "generated_at_utc" in data:
        fail("suite-input must not contain generated_at_utc (removed per FND-06)")
    ok("suite-input no generated_at_utc")

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
    if 'pip download --no-deps --dest /tmp/wheels "power-framework[semantic,rerank]' not in docker_text:
        fail("Dockerfile must pip download power-framework[semantic,rerank]")
    ok("Dockerfile pip download uses [semantic,rerank]")
    if f'echo "${{POWER_FRAMEWORK_WHEEL_SHA256}}  /tmp/wheels/power_framework-{power_version}-py3-none-any.whl" | sha256sum -c -' not in docker_text:
        fail("Dockerfile must verify POWER wheel sha256 via sha256sum -c")
    ok("Dockerfile verifies wheel hash")
    if '"/tmp/wheels/power_framework-3.7.4-py3-none-any.whl[semantic,rerank]"' not in docker_text:
        fail("Dockerfile must pip install wheel[semantic,rerank]")
    ok("Dockerfile pip install uses [semantic,rerank]")
    for dep in ["onnxruntime", "tokenizers", "huggingface_hub", "numpy", "fastembed"]:
        if f"find_spec('{dep}')" not in docker_text:
            fail(f"Dockerfile missing assert find_spec('{dep}')")
    ok("Dockerfile asserts all 5 deps (onnxruntime, tokenizers, huggingface_hub, numpy, fastembed)")

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
    if 'pip download --no-deps --dest /tmp/wheels "power-framework @ https://github.com/weby-homelab/power-framework/releases/download/v3.7.4/power_framework-3.7.4-py3-none-any.whl"' not in dp_text:
        fail("docker-publish.yml Install dependencies must pip download POWER wheel to /tmp/wheels")
    ok("docker-publish.yml Install downloads POWER wheel")
    if 'echo "f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2  /tmp/wheels/power_framework-3.7.4-py3-none-any.whl" | sha256sum -c -' not in dp_text:
        fail("docker-publish.yml must verify wheel sha via sha256sum -c")
    ok("docker-publish.yml verifies wheel hash before install")
    if "pip install --no-cache-dir \"/tmp/wheels/power_framework-3.7.4-py3-none-any.whl\"" not in dp_text:
        fail("docker-publish.yml must pip install from /tmp/wheels with verified file")
    ok("docker-publish.yml installs verified wheel")
    if "Validate suite-input drift" not in dp_text:
        fail("docker-publish.yml must contain Validate suite-input drift step")
    ok("docker-publish.yml has validator step")

    # 3. .github/workflows/release.yml
    release_yml = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    if 'assert power_gui.__version__ == "0.7.10"' in release_yml:
        fail("release.yml still hard-coded 0.7.10")
    ok("release.yml not hard-coded 0.7.10")
    if "GITHUB_REF_NAME" not in release_yml:
        fail("release.yml must derive expected from GITHUB_REF_NAME")
    ok("release.yml version-agnostic")

    # 4. compatibility.json
    compat_data = json.loads(COMPAT.read_text(encoding="utf-8"))
    if compat_data["power_core"]["dependency"]["revision"] != power_commit:
        fail(f"compatibility.json power_core.dependency.revision {compat_data['power_core']['dependency']['revision']} != {power_commit}")
    ok("compatibility.json power_core revision matches")
    if compat_data["power_core"]["dependency"]["wheel_sha256"] != power_wheel_sha:
        fail("compatibility.json wheel_sha256 mismatch")
    ok("compatibility.json wheel_sha256 matches")
    if compat_data["power_gui"]["version"] != gui_version:
        fail(f"compatibility.json power_gui.version {compat_data['power_gui']['version']} != {gui_version}")
    ok("compatibility.json gui version matches")
    if compat_data["power_gui"]["candidate_revision"] is not None:
        fail(f"compatibility.json power_gui.candidate_revision should be null (got {compat_data['power_gui']['candidate_revision']})")
    ok("compatibility.json candidate_revision null (resolved from tag at publication)")
    if compat_data["power_core"]["candidate_revision"] is not None:
        fail(f"compatibility.json power_core.candidate_revision should be null (got {compat_data['power_core']['candidate_revision']})")
    ok("compatibility.json power_core candidate_revision null")
    if compat_data["container"]["constraints_sha256"] != constraints_sha:
        fail("compatibility.json container.constraints_sha256 mismatch")
    ok("compatibility.json constraints_sha matches")
    if compat_data["container"]["image"] != f"webyhomelab/power-gui:{gui_version}":
        fail(f"compatibility.json container image {compat_data['container']['image']} != webyhomelab/power-gui:{gui_version}")
    ok("compatibility.json container image matches")
    if "[semantic,rerank]" not in compat_data["power_core"]["version_strategy"]:
        fail("compatibility.json version_strategy must contain [semantic,rerank]")
    ok("compatibility.json version_strategy [semantic,rerank]")
    if compat_data["verification"]["local_candidate_gui"] != "GUI 0.7.12 corrective patch binds exact final POWER wheel; signed commit, tag, and image digest readback remain release gates":
        fail("compatibility.json verification local_candidate_gui stale (should be 0.7.12)")
    ok("compatibility.json verification 0.7.12")

    # 5. constraints file sha
    constraints_bytes = CONSTRAINTS.read_bytes()
    actual_constraints_sha = hashlib.sha256(constraints_bytes).hexdigest()
    if actual_constraints_sha != constraints_sha:
        fail(f"constraints file sha {actual_constraints_sha} != suite-input {constraints_sha}")
    ok("constraints file sha matches suite-input")
    constraints_text = CONSTRAINTS.read_text(encoding="utf-8")
    if f"power-framework=={power_version}" not in constraints_text:
        fail(f"constraints missing power-framework=={power_version}")
    ok("constraints contains power-framework pin")
    if f"power-gui=={gui_version}" not in constraints_text:
        fail(f"constraints missing power-gui=={gui_version}")
    ok("constraints contains power-gui pin")

    # 6. pyproject.toml
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'version = "([^"]+)"', pyproject_text)
    if not m:
        fail("pyproject.toml missing version")
    if m.group(1) != gui_version:
        fail(f"pyproject.toml version {m.group(1)} != suite-input gui version {gui_version}")
    ok("pyproject.toml version matches suite-input")
    if (
        f'"power-framework=={power_version}"' not in pyproject_text
        and f"'power-framework=={power_version}'" not in pyproject_text
        and f"power-framework=={power_version}" not in pyproject_text
    ):
        fail("pyproject.toml missing power-framework==3.7.4 dependency")
    ok("pyproject.toml power-framework dependency matches")

    # 7. src/power_gui/__init__.py
    init_text = (ROOT / "src" / "power_gui" / "__init__.py").read_text(encoding="utf-8")
    m_init = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    if not m_init or m_init.group(1) != gui_version:
        fail(f"src/power_gui/__init__.py __version__ {m_init.group(1) if m_init else 'missing'} != {gui_version}")
    ok("src/power_gui/__init__.py version matches suite-input")

    # 8. uv.lock
    uv_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    if f'name = "power-gui"' not in uv_text or f'version = "{gui_version}"' not in uv_text:
        fail(f"uv.lock missing power-gui version {gui_version}")
    ok("uv.lock power-gui version matches")
    if "13dd835be5f5a03b13cad4a627b0445b2451acf0" not in uv_text:
        fail("uv.lock missing power-framework rev 13dd835")
    ok("uv.lock power-framework rev matches")

    # 9. release notes
    notes_path = ROOT / f"release/release-{gui_version}.md"
    if not notes_path.is_file():
        fail(f"release notes {notes_path} missing for {gui_version}")
    notes_text = notes_path.read_text(encoding="utf-8")
    if "[semantic,rerank]" not in notes_text:
        fail("release notes must contain [semantic,rerank] (not [semantic] alone)")
    ok("release notes contain [semantic,rerank]")
    if "Murge" in notes_text:
        fail("release notes contains typo Murge")
    ok("release notes no Murge typo")
    if "F00-F22" in notes_text or "P14" in notes_text:
        fail("release notes contains stale F00-F22/P14 controller wording")
    ok("release notes controller wording updated to Sxx")

    # 10. README.md
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"webyhomelab/power-gui:{gui_version}" not in readme_text:
        fail(f"README.md missing image webyhomelab/power-gui:{gui_version}")
    ok("README.md image matches")
    if 'softwareVersion: 0.7.10' in readme_text:
        fail("README.md still contains stale softwareVersion 0.7.10")
    ok("README.md no stale 0.7.10")
    if "GUI `0.7.11`" in readme_text:
        fail("README.md still contains stale GUI 0.7.11")
    ok("README.md GUI version 0.7.12 candidate")
    if "publication pending" not in readme_text or "Suite certification pending" not in readme_text:
        fail("README.md must contain publication pending and Suite certification pending for candidate")
    ok("README.md publication pending wording")

    # 11. README.ua.md
    readme_ua_text = (ROOT / "README.ua.md").read_text(encoding="utf-8")
    if f"webyhomelab/power-gui:{gui_version}" not in readme_ua_text:
        fail(f"README.ua.md missing image webyhomelab/power-gui:{gui_version}")
    ok("README.ua.md image matches")
    if "webyhomelab/power-gui:0.7.10" in readme_ua_text:
        fail("README.ua.md still contains stale 0.7.10")
    ok("README.ua.md no stale 0.7.10")

    # 12. docker-compose.yml
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    if f"image: webyhomelab/power-gui:{gui_version}" not in compose_text:
        fail(f"docker-compose.yml missing image webyhomelab/power-gui:{gui_version}")
    ok("docker-compose.yml image matches")
    if "NET_ADMIN" in compose_text or "NET_RAW" in compose_text:
        fail("docker-compose.yml must not contain NET_ADMIN/NET_RAW (should be cap_drop ALL only)")
    ok("docker-compose.yml no NET_ADMIN/NET_RAW")
    if "cap_drop:" not in compose_text or "- ALL" not in compose_text:
        fail("docker-compose.yml must contain cap_drop ALL")
    ok("docker-compose.yml cap_drop ALL preserved")
    if "read_only: true" not in compose_text:
        fail("docker-compose.yml must contain read_only: true")
    ok("docker-compose.yml read_only true")

    print("\nAll suite-input drift checks PASS. suite-input is authoritative and all duplicates match.")


if __name__ == "__main__":
    main()
