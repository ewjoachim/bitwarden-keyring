import base64
import json

import pytest

from bitwarden_keyring import backend


# Ensure any call to a subprocess would be caught
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
    ) -> backend.Credentials:
        credentials: backend.Credentials = {
            "id": id,
            "login": {"username": username, "password": password},
        }
        if name:
            credentials["name"] = name
        return credentials

    return f


@pytest.mark.parametrize("path, expected", [(None, False), ("yay", True)])
def test_bitwarden_cli_installed(path, expected):

    assert backend.bitwarden_cli_installed(which_callable=lambda cmd: path) == expected


def test_ask_for_session(fake_process):
    fake_process.register(["bw", "unlock", "--raw"], stdout="yay")

    assert backend.ask_for_session("unlock") == "yay"


@pytest.mark.parametrize(
    "output, expected",
    [
        ("{}", False),
        ("Username or password is incorrect.", True),
        ("Invalid master password.", True),
    ],
)
def test_wrong_password(output, expected):
    assert backend.wrong_password(output) == expected


@pytest.mark.parametrize(
    "session, args",
    [(None, ["bw", "yay", "ho"]), ("foo", ["bw", "--session", "foo", "yay", "ho"])],
)
def test_bw_args(mocker, session, args):

    assert backend.bw_args("yay", "ho", session=session) == args


def test_bw_run(fake_process):
    fake_process.register(["a", "b", "c"])

    assert backend.bw_run("a", "b", "c")


def test_bw(fake_process):
    fake_process.register(["bw", "a", "b", "c"], stdout="foo")

    assert backend.bw("a", "b", "c") == "foo"


def test_bw_error(fake_process):
    fake_process.register(["bw", "foo", "bar"], returncode=1, stdout="Error")

    with pytest.raises(ValueError):
        backend.bw("foo", "bar")


def test_bw_wrong_password(fake_process):
    fake_process.register(
        ["bw", "foo", "bar"], returncode=1, stdout="Username or password is incorrect"
    )
    fake_process.register(["bw", "foo", "bar"], stdout="{}")

    assert backend.bw("foo", "bar") == "{}"


def test_match_credentials():
    assert list(
        backend.match_credentials(
            [  # pyright: ignore[reportArgumentType]
                {"a": "b"},
                {"login": {"username": "bla"}},
                {"login": {"username": "myname"}, "ha": "ho"},
                {"login": {"username": "myname", "password": "hi"}, "ha": "ho"},
            ],
            "myname",
        )
    ) == [{"login": {"username": "myname", "password": "hi"}, "ha": "ho"}]


@pytest.mark.parametrize(
    "matches, expected",
    [([], None), ([{"foo": "a"}], None), ([{"login": {"password": "a"}}], "a")],
)
def test_select_single_match(matches, expected):
    assert backend.select_single_match(matches) == expected


def test_select_single_match_error(cred):
    with pytest.raises(ValueError):
        assert backend.select_single_match([cred(), cred()])


def test_display_credentials(cred):
    assert (
        backend.display_credentials(
            {
                "1": cred(username="baz"),
                "2": cred(name="foo", username="bar"),
            }
        )
        == "1) no name - baz\n2) foo - bar"
    )


@pytest.mark.parametrize(
    "cred, expected",
    [
        ({"login": {"username": "yay"}}, "no name - yay"),
        ({"name": "foo", "login": {"username": "yo"}}, "foo - yo"),
    ],
)
def test_display_credential(cred, expected):
    assert backend.display_credential(cred) == expected


def test_select_from_multiple_matches(cred):
    result = backend.select_from_multiple_matches(
        matches=[cred(password="foo")], input_callable=lambda x: "1"
    )
    assert result == "foo"


def test_select_match_single__empty():

    assert backend.select_match([], input_callable=lambda x: "1") is None


def test_select_match_multiple(cred):
    assert (
        backend.select_match(
            [cred(password="foo"), cred(password="bar")], input_callable=lambda x: "1"
        )
        == "foo"
    )


def test_get_session_environ(fake_process):
    fake_process.register(["bw", "sync"])
    assert backend.get_session({"BW_SESSION": "bla"}) == "bla"


def test_get_session_unauthenticated_with_env(fake_process):
    fake_process.register(["bw", "sync"], returncode=1)
    fake_process.register(["bw", "login", "--check"], returncode=1)
    fake_process.register(["bw", "login", "--raw"], stdout="foo")

    assert backend.get_session({"BW_SESSION": "bla"}) == "foo"


def test_get_session_authenticated_with_env(fake_process):
    fake_process.register(["bw", "sync"])

    assert backend.get_session({"BW_SESSION": "bla"}) == "bla"


def test_get_session_unauthenticated_without_env(fake_process):
    fake_process.register(["bw", "login", "--check"], returncode=1)
    fake_process.register(["bw", "login", "--raw"], stdout="foo")

    assert backend.get_session({}) == "foo"


def test_get_session_authenticated_without_env(fake_process):
    fake_process.register(["bw", "login", "--check"])
    fake_process.register(["bw", "unlock", "--raw"], stdout="foo")

    assert backend.get_session({}) == "foo"


def test_confirm_delete_yes(fake_process, cred, capsys):
    fake_process.register(["bw", "--session", "yo", "delete", "item", "foo"])

    backend.confirm_delete(
        session="yo", credential=cred(id="foo"), input_callable=lambda x: "yes"
    )

    assert "Deleted." in capsys.readouterr().out


def test_confirm_delete_no(fake_process, cred, capsys):
    backend.confirm_delete(
        session="yo", credential=cred(id="foo"), input_callable=lambda x: "no"
    )

    assert "Cancelled." in capsys.readouterr().out


@pytest.mark.parametrize(
    "is_authenticated, command", [(False, "login"), (True, "unlock")]
)
def test_ask_for_session_command(is_authenticated, command):
    assert backend.ask_for_session_command(is_authenticated=is_authenticated) == command


def test_get_password(fake_process, cred):
    fake_process.register(["bw", "sync"])
    fake_process.register(["bw", "--session", "bla", "sync"])
    fake_process.register(
        ["bw", "--session", "bla", "list", "items", "--search", "foo"],
        stdout=json.dumps([cred(name="foo", username="bar", password="baz")]),
    )

    assert backend.get_password("foo", "bar", _environ={"BW_SESSION": "bla"}) == "baz"


def test_encode():
    assert backend.encode({"yay": "ho"}) == "eyJ5YXkiOiAiaG8ifQ=="
    assert json.loads(base64.b64decode(backend.encode({"yay": "ho"}))) == {"yay": "ho"}


def test_set_password(fake_process):
    fake_process.register(["bw", "sync"])
    fake_process.register(
        ["bw", "--session", "bla", "get", "template", "item"], stdout='{"a": "b"}'
    )
    payload = (
        "eyJhIjogImIiLCAibmFtZSI6ICJmb28iLCAibm90ZXMiOiBudWxsLCAibG9naW4iOiB7"
        "InVyaXMiOiBbeyJtYXRjaCI6IG51bGwsICJ1cmkiOiAiZm9vIn1dLCAidXNlcm5hbWUi"
        "OiAiYmFyIiwgInBhc3N3b3JkIjogImJheiJ9fQ=="
    )

    fake_process.register(["bw", "create", "item", payload])

    backend.set_password("foo", "bar", "baz", _environ={"BW_SESSION": "bla"})

    assert json.loads(base64.b64decode(payload).decode("utf-8")) == {
        "name": "foo",
        "login": {
            "username": "bar",
            "uris": [{"match": None, "uri": "foo"}],
            "password": "baz",
        },
        "a": "b",
        "notes": None,
    }


def test_delete_password(fake_process, cred):
    fake_process.register(["bw", "sync"])
    fake_process.register(["bw", "--session", "bla", "sync"])
    fake_process.register(
        ["bw", "--session", "bla", "get", "item", "foo"], stdout=json.dumps(cred())
    )
    fake_process.register(["bw", "--session", "bla", "delete", "item", "id"])

    backend.delete_password(
        "foo", "bar", _environ={"BW_SESSION": "bla"}, _input_callable=lambda x: "yes"
    )


def test_bitwarden_backend_prio_not_installed(mocker):
    mocker.patch(
        "bitwarden_keyring.backend.bitwarden_cli_installed", return_value=False
    )
    with pytest.raises(RuntimeError):
        backend.BitwardenBackend.priority  # noqa: B018


def test_bitwarden_backend_prio_installed(mocker):
    mocker.patch("bitwarden_keyring.backend.bitwarden_cli_installed", return_value=True)

    assert backend.BitwardenBackend.priority == 10


def test_bitwarden_backend_get_password(mocker):
    get_password = mocker.patch("bitwarden_keyring.backend.get_password")

    assert (
        backend.BitwardenBackend().get_password("a", "b") == get_password.return_value
    )
    get_password.assert_called_with("a", "b")


def test_bitwarden_backend_set_password(mocker):
    set_password = mocker.patch("bitwarden_keyring.backend.set_password")

    assert (
        backend.BitwardenBackend().set_password("a", "b", "c")
        == set_password.return_value
    )
    set_password.assert_called_with("a", "b", "c")


def test_bitwarden_backend_delete_password(mocker):
    delete_password = mocker.patch("bitwarden_keyring.backend.delete_password")

    assert (
        backend.BitwardenBackend().delete_password("a", "b")
        == delete_password.return_value
    )
    delete_password.assert_called_with("a", "b")
