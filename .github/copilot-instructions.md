# Copilot instructions — HA-LocalAI-Monitor

> Canonical standards live in the `dev-standards` repo on SOUNDWAVE/Gitea.
> Read by Copilot chat **and** inline suggestions. For full HA build conventions,
> see the `build-ha-component` skill in dev-standards.

## What this repo is

A **Home Assistant custom component** — coordinator-based sensors that monitor a
LocalAI server. Domain: `localai_monitor`.

## Repo shape

- `custom_components/localai_monitor/` — `manifest.json`, `__init__.py`,
  `config_flow.py`, `const.py`, `coordinator.py`, `sensor.py`, `services.yaml`,
  `strings.json`, `translations/`, `brand/`.
- `hacs.json`, `.github/workflows/` (validate + release).

## Housekeeping

- A `__pycache__/` directory is currently committed under the component — it
  shouldn't be in version control. Add `__pycache__/` + `*.pyc` to `.gitignore`
  and remove the tracked copies.

## Conventions

- Bump `manifest.json` **version** every release (semver); `domain` matches the
  folder name.
- Test: `hassfest` + HACS validation, then `pytest` with
  `pytest-homeassistant-custom-component`.
- Deploy/test via the published release artifact into TEST1/TEST2, not host
  file-copy. Backup + auto-rollback.
- LocalAI endpoint/credentials are user config — never commit them.

## Never

- Don't commit HA long-lived tokens or deploy keys — Gitea Actions secrets only.
