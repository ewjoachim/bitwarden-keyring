import base64
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from typing import Any, Protocol, TypedDict, cast

from jaraco.classes import properties
from keyring import backend

if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired

PRIORITY = 10.0  # Doc is oddly vague
BW_CLI = "bw"


class Login(TypedDict):
    username: str
    password: str


class Credentials(TypedDict):
    id: str
    name: NotRequired[str]
    login: Login


def user_is_authenticated() -> bool:
    try:
        bw_run(*bw_args("login", "--check"))
    except subprocess.CalledProcessError:
        return False
    return True


class WhichCallable(Protocol):
    def __call__(self, cmd: str) -> str | None: ...


def bitwarden_cli_installed(which_callable: WhichCallable = shutil.which) -> bool:
    return bool(which_callable(BW_CLI))


def ask_for_session(command: str) -> str:
    result = bw(command, "--raw")
    return result


def ask_for_session_command(is_authenticated: bool) -> str:
    return "unlock" if is_authenticated else "login"


def wrong_password(output: str) -> bool:
    return bool(
        "Username or password is incorrect" in output
        or "Invalid master password" in output
    )


def bw_args(*args: str, session: str | None = None):
    cli_args = [BW_CLI]
    if session:
        cli_args += ["--session", session]

    return [*cli_args, *args]


def bw_run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, stdout=subprocess.PIPE, check=True, text=True)


def bw(*args: str, session: str | None = None) -> str:

    cli_args = bw_args(*args, session=session)

    while True:
        try:
            result = bw_run(*cli_args).stdout.strip()
        except subprocess.CalledProcessError as exc:
            output = cast(str, exc.stdout)
            if wrong_password(output):
                print(output)
                continue
            raise ValueError(output) from exc
        else:
            break

    return result


def match_credentials(
    credentials: list[Credentials], username: str
) -> Iterable[Credentials]:
    for cred in credentials:
        login = cred.get("login") or {}
        cred_username = login.get("username")
        if cred_username == username and "password" in login:
            yield cred


def select_single_match(matches: list[Credentials]) -> str | None:
    if len(matches) == 0:
        return

    if len(matches) == 1:
        (match,) = matches
        try:
            return match["login"]["password"]
        except KeyError:
            return None

    raise ValueError("Multiple matches")


def display_credentials(mapping: dict[str, Credentials]) -> str:
    result: list[str] = []
    for val, match in mapping.items():
        result.append(f"{val}) {display_credential(match)}")

    return "\n".join(result)


def display_credential(match: Credentials) -> str:
    return f"{match.get('name', 'no name')} - {match['login']['username']}"


class InputCallable(Protocol):
    def __call__(self, prompt: str = "", /) -> str: ...


def select_from_multiple_matches(
    matches: list[Credentials], input_callable: InputCallable
) -> str | None:
    print("Multiple credential found. Which one would you like to use ?")
    mapping: dict[str, Credentials] = {str(i): v for i, v in enumerate(matches, 1)}
    print(display_credentials(mapping))
    value = input_callable("Your choice ? ")
    return mapping[value]["login"]["password"]


def select_match(
    matches: list[Credentials], input_callable: InputCallable
) -> str | None:
    try:
        return select_single_match(matches)
    except ValueError:
        return select_from_multiple_matches(matches, input_callable=input_callable)


def encode(payload: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def get_session(environ: Mapping[str, str]) -> str:
    if "BW_SESSION" in environ:
        try:
            # Check that the token works.
            bw("sync")
        except ValueError:
            pass
        else:
            return environ["BW_SESSION"]

    command = ask_for_session_command(is_authenticated=user_is_authenticated())
    return ask_for_session(command=command)


def get_password(
    service: str,
    username: str,
    _input_callable: InputCallable = input,
    _environ: Mapping[str, str] = os.environ,
) -> str | None:
    session = get_session(_environ)

    # Making sure we're up to date
    bw("sync", session=session)

    results = bw("list", "items", "--search", service, session=session)

    credentials = cast(list[Credentials], json.loads(results))

    matches = list(match_credentials(credentials, username))

    return select_match(matches, input_callable=_input_callable)


def set_password(
    service: str,
    username: str,
    password: str,
    _environ: Mapping[str, str] = os.environ,
) -> None:
    session = get_session(_environ)

    template_str = bw("get", "template", "item", session=session)

    template = json.loads(template_str)
    template.update(
        {
            "name": service,
            "notes": None,
            "login": {
                "uris": [{"match": None, "uri": service}],
                "username": username,
                "password": password,
            },
        }
    )

    payload = encode(template)

    bw("create", "item", payload)
    print("Created.")


def confirm_delete(
    session: str, credential: Credentials, input_callable: InputCallable
) -> None:

    print("The following match will be DELETED:")
    print(display_credential(credential))
    if input_callable("Confirm ? (type 'yes')").lower() == "yes":
        bw("delete", "item", credential["id"], session=session)
        print("Deleted.")
        return
    print("Cancelled.")


def delete_password(
    service: str,
    username: str,
    _input_callable: InputCallable = input,
    _environ: Mapping[str, str] = os.environ,
) -> None:
    session = get_session(_environ)

    bw("sync", session=session)

    result = bw("get", "item", service, session=session)

    credential = json.loads(result)

    confirm_delete(session, credential, input_callable=_input_callable)


class BitwardenBackend(backend.KeyringBackend):
    @properties.classproperty
    @classmethod
    def priority(cls) -> float:
        if not bitwarden_cli_installed():
            raise RuntimeError(
                "Requires bitwarden cli: https://help.bitwarden.com/article/cli/"
            )

        return PRIORITY

    def get_password(self, service: str, username: str) -> str | None:
        return get_password(service, username)

    def set_password(self, service: str, username: str, password: str) -> None:
        return set_password(service, username, password)

    def delete_password(self, service: str, username: str) -> None:
        return delete_password(service, username)
