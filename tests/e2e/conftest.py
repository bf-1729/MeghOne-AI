import os

import pytest


@pytest.hookimpl(tryfirst=True)  # must run before pytest's "-m e2e" filtering
def pytest_collection_modifyitems(config, items):
    """Mark everything under tests/e2e as e2e, and skip it when no app is running."""
    base_url = config.getoption("base_url", default=None) or os.environ.get("BASE_URL")
    skip = pytest.mark.skip(reason="No running app (BASE_URL not set) - E2E skipped")
    for item in items:
        if "tests/e2e" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.e2e)
            if not base_url:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Use --base-url if given, else the BASE_URL env var set by scripts/ci/start_app.sh."""
    return pytestconfig.getoption("base_url", default=None) or os.environ.get("BASE_URL")
