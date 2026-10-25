# heartbeat-service

A small FastAPI service. It's the target repository for testing a Claude-based
pull-request security reviewer: the application is ordinary on purpose, so that
security-relevant changes in a PR stand out.

## Layout

```
app/
  main.py          FastAPI app factory + lifespan that runs the heartbeat
  config.py        Settings (env vars / .env)
  heartbeat.py     Background task: appends a timestamped line to logs/heartbeat.log
  api/routes.py    GET /health, GET /info
tests/             Unit tests for the API and the heartbeat
.github/workflows/ PR checks: tests, dependency audit, static analysis
docs/              Reviewer integration guide (and threat model, see below)
```

## Setup

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # optional
```

## Run

```bash
uvicorn app.main:app --reload
curl localhost:8000/health   # {"status":"ok"}
tail -f logs/heartbeat.log
```

The heartbeat writes one line on startup and then one every
`HEARTBEAT_INTERVAL_SECONDS` (default `300`, i.e. five minutes):

```
2026-10-25T10:00:00.123456+00:00 heartbeat
```

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `heartbeat-service` | Returned by `/info` |
| `APP_ENV` | `development` | Returned by `/info` |
| `HEARTBEAT_ENABLED` | `true` | Turn the background task off |
| `HEARTBEAT_INTERVAL_SECONDS` | `300` | Seconds between heartbeats |
| `HEARTBEAT_LOG_PATH` | `logs/heartbeat.log` | Output file (parent dirs created) |

## Test and check locally

```bash
pytest                       # unit tests
pip-audit -r requirements.txt
bandit -r app -ll
```

## CI

`.github/workflows/pr-checks.yml` runs on every pull request:

- **tests**: `pytest`
- **dependency-audit**: `pip-audit` against `requirements.txt`
- **static-analysis**: `bandit` on `app/` (this check gates the PR)

See [docs/CLAUDE_PR_REVIEWER.md](docs/CLAUDE_PR_REVIEWER.md) to add the Claude reviewer.
