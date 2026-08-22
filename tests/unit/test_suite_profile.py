"""Static suite-profile guardrails for the native and container GUI surfaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
POWER_SHA = "13dd835be5f5a03b13cad4a627b0445b2451acf0"
POWER_WHEEL_SHA = "f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2"
CONSTRAINTS_SHA = "33977cd71397cf4f52399d4923c067bd7f0f9199eebbf7351adeb095a1f30456"


def test_native_service_is_user_scoped_loopback_and_opt_in() -> None:
    service = (ROOT / "power-gui.service").read_text(encoding="utf-8")
    assert "User=" not in service
    assert "Group=" not in service
    assert "WantedBy=default.target" in service
    assert "ExecStart=%h/.local/bin/power-gui" in service
    assert "--vault" not in service
    assert "EnvironmentFile=-%h/.config/power-gui.env" in service
    assert "Restart=on-failure" in service
    assert "Restart=always" not in service


def test_container_profile_is_pinned_non_root_and_health_checked() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f"ARG POWER_FRAMEWORK_COMMIT={POWER_SHA}" in dockerfile
    assert f"ARG POWER_FRAMEWORK_WHEEL_SHA256={POWER_WHEEL_SHA}" in dockerfile
    assert "COPY release/power-suite.constraints.txt /app/power-suite.constraints.txt" in dockerfile
    assert "--constraint /app/power-suite.constraints.txt" in dockerfile
    assert "pip download" in dockerfile or "power_framework-3.7.4-py3-none-any.whl" in dockerfile
    constraints = (ROOT / "release" / "power-suite.constraints.txt").read_bytes()
    assert hashlib.sha256(constraints).hexdigest() == CONSTRAINTS_SHA
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "POWER_GUI_HOST=0.0.0.0" in dockerfile
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'user: "10001:10001"' in compose
    assert "no-new-privileges:true" in compose
    assert "- ALL" in compose


def test_compatibility_manifest_does_not_claim_unpublished_digest() -> None:
    manifest = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
    assert manifest["power_core"]["candidate_version"] == "3.7.4"
    assert manifest["power_core"]["dependency"]["revision"] == POWER_SHA
    assert manifest["power_core"]["dependency"]["tag"] == "v3.7.4"
    assert manifest["power_core"]["dependency"]["wheel_sha256"] == POWER_WHEEL_SHA
    assert manifest["power_core"]["candidate_publication_required"] is False
    assert manifest["power_gui"]["version"] == "0.7.12"
    assert manifest["power_gui"]["release_tag"] is None
    assert manifest["container"]["digest"] is None
    assert manifest["container"]["digest_status"] == "not_published"
    assert manifest["container"]["constraints_sha256"] == CONSTRAINTS_SHA
    suite_input = json.loads(
        (ROOT / "release" / "power.gui.suite-input.json").read_text(encoding="utf-8")
    )
    assert suite_input["schema"] == "power.gui.suite-input.v1"
    assert suite_input["power"]["source_sha"] == POWER_SHA
    assert suite_input["power"]["wheel_sha256"] == POWER_WHEEL_SHA
    assert suite_input["gui"]["version"] == "0.7.12"
    assert suite_input["constraints"]["sha256"] == CONSTRAINTS_SHA
    assert POWER_SHA not in ("eb8afbfdc9f067e7b11b8679390e1327a9becf6c", "main", "latest")


def test_accessibility_profile_has_focus_motion_and_form_guardrails() -> None:
    css = (ROOT / "src/power_gui/static/css/style.css").read_text(encoding="utf-8")
    base = (ROOT / "src/power_gui/templates/base.html").read_text(encoding="utf-8")
    graph = (ROOT / "src/power_gui/templates/graph.html").read_text(encoding="utf-8")
    search = (ROOT / "src/power_gui/templates/search.html").read_text(encoding="utf-8")
    decisions = (ROOT / "src/power_gui/templates/decisions.html").read_text(encoding="utf-8")

    assert "transition: all" not in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".skip-link" in base and 'id="main-content" tabindex="-1"' in base
    assert "outline: none" not in base
    for control_id in ("graphSearchInput", "graphCategorySelect", "graphDegreeSelect"):
        assert f'for="{control_id}"' in graph
    assert 'for="searchQuery"' in search and 'id="searchQuery"' in search
    assert 'for="decisionInputValue"' in decisions and 'id="decisionInputValue"' in decisions
