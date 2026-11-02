# Ship config

How this repo goes from branch to users. Read by the `jeebzstack` plugin at every stage. Keep it true; it ships through PRs like everything else.

Public repo. Product direction, roadmap, pricing and specs live in Notion, never here.

## Checks

The gate. Mirrors `.github/workflows/ci.yml` (Python 3.10, 3.11, 3.12), so a green local run means a green CI run.

- `pip install -e "cli[dev]" ruff`
- `ruff check cli/src`
- `pytest cli/tests -q`

Landing page changes (not in CI yet, inferred, check):

- `cd landing-page && npm ci && npm run lint && npm run build`

## Prove it

How to run the real thing to see a change working.

- Build/run: `pip install -e cli && python examples/fragile-shop.py 8400` in one terminal
- Smoke: `prescale investigate http://localhost:8400 --path /search --path /product --path /checkout -u 60 -s 2`; expect `/checkout` named as the culprit with a `connection_pool` diagnosis while static assets hold
- JSON contract: `prescale show --json` (or `run --json`) validates against `prescale schema`
- Landing page: `cd landing-page && npm run build && npm run preview`, open the printed URL

## Risky paths

Touching these makes a change **risky tier**: rollback written first, fresh-context review.

- `landing-page/public/install`, `landing-page/public/install.ps1`: strangers pipe them to `sh` / `iex`; a bad line breaks every install
- `action/action.yml`: runs inside other people's CI with their `PRESCALE_TOKEN` and PR write access; users pin `@v1`, so a change reaches them without a release
- `cli/src/prescale_cli/schema/result.schema.json`, `cli/src/prescale_cli/result.py`: the public JSON contract that saved runs, `--json` consumers, MCP and the dashboard's ingest depend on; additive changes only (`schema_version` stays 1)
- `cli/src/prescale_cli/cloud.py`, `commands/upload.py`, `commands/login.py`: the data boundary and credentials; a mistake uploads something the README promises never leaves the machine
- `cli/src/prescale_cli/hosts.py`, `mcp_tools.py` (allowlist), the non-local confirm in `commands/run.py`: safety rails; failing open sends load to hosts that forbid it, silently
- `cli/src/prescale_cli/replica.py`: starts and kills the user's processes; a bug leaves servers running or kills the wrong thing
- CLI commands, flags and `--json` output: public interface, scripted against in CI
- Journey files (`prescale/journeys/*.yaml`, once they exist) and their loader: a format users commit to their repos
- `.github/workflows/release.yml`: publishes to PyPI and creates releases
- `landing-page/vercel.json`: routes prescale.dev, `/install`, `/docs` and `/dashboard`; a bad rewrite takes the site, installer or dashboard down

## Deploy

How a merge reaches users, and how to know it worked.

- Landing page: auto on merge to `main` via Vercel (`landing-page/`) (inferred, check)
  - Check: `curl -fsSI https://prescale.dev` → 200; `curl -fsSL https://prescale.dev/install | head -3` → the installer's shebang; `curl -fsSI https://prescale.dev/docs` → 200
  - Rollback: promote the previous deployment in Vercel, then revert the PR
- Docs: `docs/` is served by Mintlify, proxied at `/docs` (inferred, check)
- GitHub Action: users run `pyjeebz/prescale/action@v1` from this repo; it pip-installs the CLI from PyPI. A change to `action/` reaches users when the `v1` tag moves
- CLI: no deploy; reaches users through a release
- Dashboard: separate private repo, not deployed from here

## Release

- Bump the version in all three places: `pyproject.toml`, `cli/pyproject.toml`, `cli/src/prescale_cli/__init__.py`
- Add a dated entry to `CHANGELOG.md`: `## X.Y.Z — YYYY-MM-DD` (the release workflow refuses to publish without it)
- Trigger: push tag `vX.Y.Z` → `.github/workflows/release.yml` → PyPI (trusted publishing), then a GitHub release with notes from that changelog section
- Then move the Action's major tag: `git tag -f v1 vX.Y.Z && git push -f origin v1` (only when the Action should pick up the release)
- Channels to verify: `pip install prescale==X.Y.Z`; `curl -fsSL https://prescale.dev/install | sh` then `prescale --version`; the GitHub release page; a workflow using `@v1`
