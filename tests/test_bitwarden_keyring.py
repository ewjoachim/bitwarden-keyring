import base64
import io
import json
import os

import pytest

import bitwarden_keyring as bwkr


@pytest.fixture
def bw(mocker):
    yield mocker.patch("bitwarden_keyring.bw")


@pytest.fixture
def bw_run(mocker):
    yield mocker.patch("bitwarden_keyring.bw_run")


@pytest.fixture(autouse=True)
def del_env(mocker):
    os.environ.pop("BW_SESSION", None)
    yield


@pytest.mark.parametrize("path, expected", [(None, False), ("yay", True)])
def test_bitwarden_cli_installed(mocker, path, expected):
    mocker.patch("shutil.which", return_value=path)

    assert bwkr.bitwarden_cli_installed() == expected


def test_ask_for_session(bw):
    bw.return_value = "yay"
    assert bwkr.ask_for_session("unlock") == "yay"
    bw.assert_called_with("unlock", "--raw")


@pytest.mark.parametrize(
    "output, expected",
    [
        ("{}", False),
        ("Username or password is incorrect.", True),
        ("Invalid master password.", True),
    ],
)
def test_wrong_password(output, expected):
    assert bwkr.wrong_password(output) == expected


@pytest.mark.parametrize(
    "session, args",
    [(None, ["bw", "yay", "ho"]), ("foo", ["bw", "--session", "foo", "yay", "ho"])],
)
def test_bw_args(mocker, session, args):

    assert bwkr.bw_args("yay", "ho", session=session) == args


def test_bw_run(mocker):
    run = mocker.patch("subprocess.run")

    assert bwkr.bw_run("a", "b", "c") == run.return_value

    run.assert_called_with(("a", "b", "c"), check=True, stdout=bwkr.subprocess.PIPE)


def test_bw(mocker):
    run = mocker.patch("bitwarden_keyring.bw_run")
    run.return_value.stdout = "yay"

    assert bwkr.bw("a", "b", "c") == "yay"

    run.assert_called_with("bw", "a", "b", "c")


def test_bw_error(mocker):
    run = mocker.patch("subprocess.run")
    run.side_effect = bwkr.subprocess.CalledProcessError(
        output=b"Error", cmd=None, returncode=1
    )

    with pytest.raises(ValueError):
        bwkr.bw("yay", "ho")


def test_bw_wrong_password(mocker):
    run = mocker.patch("subprocess.run")
    run.side_effect = [
        bwkr.subprocess.CalledProcessError(
            output=b"Username or password is incorrect.", cmd=None, returncode=1
        ),
        mocker.Mock(stdout="{}"),
    ]

    assert bwkr.bw("yay", "ho") == "{}"
    assert run.call_count == 2


def test_match_credentials():
    assert list(
        bwkr.match_credentials(
            [
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
    [([], None), ([{"pouet": "a"}], None), ([{"login": {"password": "a"}}], "a")],
)
def test_select_single_match(matches, expected):
    assert bwkr.select_single_match(matches) == expected


def test_select_single_match_error():
    with pytest.raises(ValueError):
        assert bwkr.select_single_match([{}, {}])


def test_display_credentials():
    assert (
        bwkr.display_credentials(
            {
                "a": {"login": {"username": "yay"}},
                "b": {"name": "pouet", "login": {"username": "yo"}},
            }
        )
        == "a) no name - yay\nb) pouet - yo"
    )


@pytest.mark.parametrize(
    "cred, expected",
    [
        ({"login": {"username": "yay"}}, "no name - yay"),
        ({"name": "pouet", "login": {"username": "yo"}}, "pouet - yo"),
    ],
)
def test_display_credential(cred, expected):
    assert bwkr.display_credential({"login": {"username": "yay"}}) == "no name - yay"


def test_select_from_multiple_matches(mocker):
    mocker.patch("bitwarden_keyring.input", return_value="1")

    assert (
        bwkr.select_from_multiple_matches(
            [{"login": {"username": "yay", "password": "ho"}}]
        )
        == "ho"
    )


def test_select_match_single(mocker):
    single = mocker.patch("bitwarden_keyring.select_single_match")

    assert bwkr.select_match([]) == single.return_value


def test_select_match_multiple(mocker):
    mocker.patch("bitwarden_keyring.select_single_match", side_effect=ValueError)
    multiple = mocker.patch("bitwarden_keyring.select_from_multiple_matches")

    assert bwkr.select_match([]) == multiple.return_value


def test_get_session_environ(bw):
    assert bwkr.get_session({"BW_SESSION": "bla"}) == "bla"


def test_get_session_environ_wrong_session(bw):
    bw.side_effect = [ValueError, "yo"]

    assert bwkr.get_session({"BW_SESSION": "bla"}) == "yo"

    assert bw.call_count == 2

    bw.assert_any_call("sync")
    bw.assert_any_call("unlock", "--raw")


def test_confirm_delete_yes(bw, mocker, capsys):
    mocker.patch("bitwarden_keyring.input", return_value="yes")

    bwkr.confirm_delete("yo", {"id": "yay", "name": "a", "login": {"username": "b"}})

    bw.assert_called_with("delete", "item", "yay", session="yo")

    assert "Deleted." in capsys.readouterr().out


def test_confirm_delete_no(bw, mocker, capsys):
    mocker.patch("bitwarden_keyring.input", return_value="")

    bwkr.confirm_delete("yo", {"id": "yay", "name": "a", "login": {"username": "b"}})

    assert not bw.called

    assert "Cancelled." in capsys.readouterr().out


@pytest.mark.parametrize(
    "is_authenticated, command", [(False, "login"), (True, "unlock")]
)
def test_ask_for_session_command(bw_run, is_authenticated, command):
    assert bwkr.ask_for_session_command(is_authenticated=is_authenticated) == command


def test_get_session(mocker):
    mocker.patch("bitwarden_keyring.user_is_authenticated", return_value=True)
    ask_for_session = mocker.patch(
        "bitwarden_keyring.ask_for_session", return_value="yo"
    )

    assert bwkr.get_session({}) == "yo"

    ask_for_session.assert_called_with(command="unlock")


def test_get_password(bw):
    bw.side_effect = [
        "mysession",
        None,
        '[{"login": {"username": "a", "password": "b"}}]',
    ]

    assert bwkr.get_password("c", "a") == "b"


def test_encode():
    assert bwkr.encode({"yay": "ho"}) == b"eyJ5YXkiOiAiaG8ifQ=="
    assert json.loads(base64.b64decode(bwkr.encode({"yay": "ho"}))) == {"yay": "ho"}


def test_set_password(bw):
    bw.side_effect = ["mysession", '{"a": "b"}', None]

    bwkr.set_password("c", "d", "e")

    payload = (
        b"eyJhIjogImIiLCAibmFtZSI6ICJjIiwgIm5vdGVzIjogbnVsbCw"
        b"gImxvZ2luIjogeyJ1cmlzIjogW3sibWF0Y2giOiBudWxsLCAidXJ"
        b"pIjogImMifV0sICJ1c2VybmFtZSI6ICJkIiwgInBhc3N3b3JkIjog"
        b"ImUifX0="
    )

    bw.assert_called_with("create", "item", payload)

    assert json.loads(base64.b64decode(payload).decode("utf-8")) == {
        "a": "b",
        "login": {
            "password": "e",
            "uris": [{"match": None, "uri": "c"}],
            "username": "d",
        },
        "name": "c",
        "notes": None,
    }


def test_delete_password(bw, mocker):
    bw.side_effect = [
        "mysession",
        None,
        '{"id": "a", "login": {"username": "b"}}',
        None,
    ]
    mocker.patch("bitwarden_keyring.input", return_value="yes")

    bwkr.delete_password("c", "d")

    bw.assert_called_with("delete", "item", "a", session="mysession")


def test_bitwarden_backend_prio_not_installed(mocker):
    mocker.patch("bitwarden_keyring.bitwarden_cli_installed", return_value=False)
    with pytest.raises(RuntimeError):
        bwkr.BitwardenBackend.priority


def test_bitwarden_backend_prio_installed(mocker):
    mocker.patch("bitwarden_keyring.bitwarden_cli_installed", return_value=True)

    assert bwkr.BitwardenBackend.priority == 10


def test_bitwarden_backend_get_password(mocker):
    get_password = mocker.patch("bitwarden_keyring.get_password")

    assert bwkr.BitwardenBackend().get_password("a", "b") == get_password.return_value
    get_password.assert_called_with("a", "b")


def test_bitwarden_backend_set_password(mocker):
    set_password = mocker.patch("bitwarden_keyring.set_password")

    assert (
        bwkr.BitwardenBackend().set_password("a", "b", "c") == set_password.return_value
    )
    set_password.assert_called_with("a", "b", "c")


def test_bitwarden_backend_delete_password(mocker):
    delete_password = mocker.patch("bitwarden_keyring.delete_password")

    assert (
        bwkr.BitwardenBackend().delete_password("a", "b")
        == delete_password.return_value
    )
    delete_password.assert_called_with("a", "b")
