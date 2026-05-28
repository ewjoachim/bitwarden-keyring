import pytest


# Ensure any call to a subprocess would be caught.
@pytest.fixture(autouse=True)
def ensure_no_process(fake_process):
    pass


@pytest.fixture(autouse=True)
def del_env(monkeypatch):
    monkeypatch.delenv("BW_SESSION", raising=False)
    yield


@pytest.fixture
def cred():
    def f(
        id: str = "id",  # noqa: A002
        name: str | None = None,
        username: str = "user",
        password: str = "password",
    ):
        credentials = {
            "id": id,
            "login": {"username": username, "password": password},
        }
        if name:
            credentials["name"] = name
        return credentials

    return f
