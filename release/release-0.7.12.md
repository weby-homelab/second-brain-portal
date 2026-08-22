# POWER-GUI 0.7.12 — Forensic Corrective Patch (Exact-Pair Closure with POWER 3.7.4)

**Suite:** POWER 3.7.4 (immutable `v3.7.4` `13dd835be5f5a03b13cad4a627b0445b2451acf0` `f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2`) + GUI 0.7.12

**Type:** corrective patch, zero material features, forensic closure for `PUBLISHED_UNCERTIFIED` → `STABLE` recertification.

## What changed vs 0.7.11 (why 0.7.12 was required)

Previous `0.7.11` public artifacts were **correct** for the core wheel (`f12ad02`) but could not satisfy mandatory shipped-artifact and workflow claims:

- **Docker semantic runtime missing (L):** `Dockerfile` did `pip download ... power-framework[semantic] @ URL` + `sha256sum -c` but then `pip install /tmp/wheels/power_framework-3.7.4-py3-none-any.whl` **without** `[semantic]` extra → `onnxruntime`, `tokenizers`, `huggingface_hub`, `numpy`, `fastembed` absent inside `03dede615677` despite Dockerfile comment "with semantic dense embeddings". Verification: `docker run --entrypoint python webyhomelab/power-gui@sha256:03dede615677... importlib` showed all 5 missing.
- **Release workflow hard-coded previous patch (F):** `.github/workflows/release.yml` at `v0.7.11` contained `assert power_gui.__version__ == "0.7.10"` and `body_path: release/release-0.7.10.md` → `GUI Release` run `32602734088` for `v0.7.11` concluded **failure**, public `0.7.11` was manually uploaded by `weby-homelab` bypassing trusted workflow (`workflow_proven=false`).
- **Release truth contradictions (A-C,E-G):** POWER `release/power.suite.release-receipt.json` still mixed `NO-GO+stable+GO` with old `0.7.7` data; POWER `release/power.suite.manifest.json` `aligned_gui.source_sha=5abe587` (first patch commit, not final `260db22`); GUI `compatibility.json` still `candidate_not_published` with `null` digest; GUI `README` still candidate wording + `0.7.10` docker examples; Suite certification `38181a9` not on `origin/main`.

`0.7.12` fixes only allowed categories (release identity, packaging, container, CI, tests, docs/evidence):

- `pyproject.toml` / `src/power_gui/__init__.py` `0.7.11` → `0.7.12`; `release/power-suite.constraints.txt` `power-gui==0.7.12` (hash `33977cd7...`); `release/power.gui.suite-input.json` `gui.version=0.7.12`, `constraints.sha256=33977cd7...` (single build-input `power.gui.suite-input.v1` controls all surfaces).
- `Dockerfile`: now `pip install --constraint ... "/tmp/wheels/power_framework-3.7.4-py3-none-any.whl[semantic]"` + `sha256sum -c` + `python -c "assert find_spec('onnxruntime'); assert find_spec('fastembed')"` proof before `rm -rf /tmp/wheels`.
- `.github/workflows/release.yml` is now **version-agnostic**: derives `expected="${GITHUB_REF_NAME#v}"` from tag, asserts `power_gui.__version__ == expected`, validates `pyproject.toml` version == expected and `release/release-${expected}.md` exists, derives `RELEASE_NOTES_PATH`, fails on mismatch; `body_path` uses `${{ env.RELEASE_NOTES_PATH }}`; readback dynamically loads `release/release-${expected}.md`.
- `uv.lock` regenerated with `power-framework` rev `13dd835`.
- `compatibility.json` remains candidate until publication (will be promoted to `published` with `release_tag=v0.7.12` + `digest` after public readback — see F16).

**No new memory subsystem, vector DB, GraphRAG, A2A, Federation, daemon, cloud control plane, canonical DB, or broad redesign.** `M2_HUMAN=EXCLUDED_BY_POLICY`, `new_material_features=0`.

## Immutable identities

- **POWER:** `v3.7.4` `13dd835be5f5a03b13cad4a627b0445b2451acf0` (tag `c2146789`, GPG `2D49E810C7F2527E`) `power_framework-3.7.4-py3-none-any.whl` `f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2` `power_framework-3.7.4.tar.gz` `6592789b6d603b39764e7127b62323966807a6c41385cf7a3024a154a197395f` `power.application.v2` `>=3.13,<3.15`
- **GUI 0.7.12:** tag `v0.7.12` → Murge commit (to be signed), `power-gui==0.7.12`, `Requires-Dist power-framework==3.7.4`, wheel/sdist deterministic (dual build `cmp` identical, `normalize_sdist.py`), `Requires-Python >=3.13,<3.15`
- **Container:** `webyhomelab/power-gui:0.7.12@sha256:<to be recorded>` must contain `power-framework 3.7.4` + `onnxruntime`/`fastembed`/`tokenizers` etc. via digest-bound `docker run @sha256:...` E2E.

## Verification gates (F00-F22)

- F00 reality freeze re-resolves both mains, tags, wheel hashes, SBOMs, digests (zero mutation).
- F02 Docker semantic runtime: proves `onnxruntime`/`fastembed` present + real disposable vault search (FTS, semantic, auto, rerank, no silent downgrade).
- F03 official release workflow: tag `v0.7.12` must trigger `GUI Release` PASS (not failure), build wheel `21225b27->new hash`, verify `public readback`.
- F04 mandatory gaps re-audited (native negatives, systemd full cycle, cross-runtime CLI+MCP+Docker, upgrade/rollback with fault injection).
- F09 native exact-pair matrix `3.13/3.14 × ASCII/spaces/Unicode` with negatives.
- F10 MCP `power-mcp` 20 tools `stdio` `stdout protocol-only` `ApplicationService(path)` + Skill `c834a360...`.
- F11 real `systemctl --user daemon-reload -> enable/start/readiness/restart/stop/disable`.
- F13 digest-bound live E2E `repository/image@sha256:<digest>` (not mutable tag).
- F14 cross-runtime `native CLI + native MCP + Docker digest + one disposable vault` 15 scenarios.
- F15 upgrade `POWER 3.7.4+GUI 0.7.11 -> POWER 3.7.4+GUI 0.7.12` with fault injection at 6 points.
- F16 rebuild release truth from clean schemas (no `NO-GO+stable` in one object, no old `0.7.7` fields, no `5abe587` mismatch, no `null` digest after published).
- F20 public consumer readback in clean context outside checkout.
- F21 durable `release/suites/power-3.7.4_gui-0.7.12/manifest.json + certification.json + validation-summary.md` on authoritative POWER `main`.

`0.7.11` remains **published but not Suite-certified** (historical, do not delete/rewrite) per Special Rule 39; `0.7.12` is the forensic corrective target.

## Upgrade

```bash
pip install --upgrade power-gui==0.7.12  # pulls exact POWER 3.7.4
# or native via manifest
power integrations install --manifest release/power.suite.manifest.json --apply --approved
# or docker
docker pull webyhomelab/power-gui:0.7.12
docker pull webyhomelab/power-gui@sha256:<digest>
```

See `compatibility.json` and Suite certification `release/suites/power-3.7.4_gui-0.7.12/` after `STABLE`.
