# Contributing to meg-6schemes

## One-time setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt        # app dependencies (once it exists)
pip install -r requirements-dev.txt    # lint/test tools
playwright install chromium            # browser for E2E tests
pre-commit install                     # run checks automatically on every commit
```

## Workflow

1. Never commit directly to `main`. Create a branch: `feature/<short-name>` or `fix/<short-name>`.
2. Commit and push your branch. The pipeline runs on every push.
3. Open a pull request into `main`. The pipeline runs again on the PR.
4. Merge only when the pipeline is green and at least one teammate approved.

## What the pipeline checks

| Check | Tool | Run it locally |
|---|---|---|
| Leaked passwords / keys | gitleaks | runs in `pre-commit` |
| Lint & formatting | ruff | `ruff check . && ruff format .` |
| Security issues in code | bandit | `bandit -c pyproject.toml -r .` |
| Vulnerable dependencies | pip-audit | `pip-audit -r requirements.txt` |
| Unit & integration tests | pytest | `pytest -m "not e2e"` |
| Browser end-to-end tests | Playwright | start the app, then `pytest -m e2e --base-url http://127.0.0.1:8000` |

## Writing tests

- Unit/integration tests: `tests/unit/test_*.py`
- Browser tests: `tests/e2e/test_*.py` (auto-marked `e2e`, use the `page` fixture)
- When an E2E test fails in the pipeline, download the step's artifacts:
  `test-results/playwright/` has the screenshot, video and trace
  (open a trace with `playwright show-trace <trace.zip>`).

## Pipeline notes

- The pipeline starts the app automatically: Django if `manage.py` exists, otherwise FastAPI
  (finds `FastAPI(` and runs `<module>:app`). To be explicit, set the repository variable
  `APP_MODULE` (e.g. `app.main:app`).
- A PostgreSQL 16 database is available to tests at `DATABASE_URL`
  (`postgres://test:test@localhost:5432/test_db`).
- Never commit `.env` or secrets. Put them in Bitbucket → Repository settings → Repository variables.
