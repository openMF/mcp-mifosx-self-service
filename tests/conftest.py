import pytest

from utils import auth


@pytest.fixture(autouse=True)
def no_saved_login(monkeypatch):
    """Every test starts logged out, with no credentials in the environment."""
    monkeypatch.delenv("MIFOS_USERNAME", raising=False)
    monkeypatch.delenv("MIFOS_PASSWORD", raising=False)
    auth.clear_login()
    yield
    auth.clear_login()
