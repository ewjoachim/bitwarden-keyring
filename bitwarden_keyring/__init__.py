import base64
import json
import os
import shutil
import subprocess

from keyring import backend
from keyring.util import properties

PRIORITY = 10  # Doc is oddly vague


def user_is_authenticated():
    return bw_run(*bw_args("login", "--check")).returncode == 0


def bitwarden_cli_installed():
    return bool(shutil.which("bw"))


def ask_for_session(command):
    result = bw(command, "--raw")
    return result


def ask_for_session_command(is_authenticated):
    return "unlock" if is_authenticated else "login"


def wrong_password(output):
    if "Username or password is incorrect" in output:
        return True
    elif "Invalid master password" in output:
        return True
    return False


def bw_args(*args, session=None):
    cli_args = ["bw"]
    if session:
        cli_args += ["--session", session]

    return cli_args + list(args)


def bw_run(*args):
    return subprocess.run(args, stdout=subprocess.PIPE, check=True)


def bw(*args, session=None):

    cli_args = bw_args(*args, session=session)

    while True:
        try:
            result = bw_run(*cli_args).stdout.strip()
        except subprocess.CalledProcessError as exc:
            output = exc.stdout.decode("utf-8")
            if wrong_password(output):
                print(output)
                continue
            raise ValueError(output) from exc
        else:
            break

    return result


def match_credentials(credentials, username):
    for cred in credentials:
        login = cred.get("login") or {}
        cred_username = login.get("username")
        if cred_username == username and "password" in login:
            yield cred


def select_single_match(matches):
    if len(matches) == 0:
        return

    if len(matches) == 1:
        match, = matches
        try:
            return match["login"]["password"]
        except KeyError:
            return None

    raise ValueError("Multiple matches")


def display_credentials(mapping):
    result = []
    for val, match in mapping.items():
        result.append(f"{val}) {display_credential(match)}")

    return "\n".join(result)


def display_credential(match):
    return f"{match.get('name', 'no name')} - {match['login']['username']}"


def select_from_multiple_matches(matches):
    print("Multiple credential found. Which one would you like to use ?")
    mapping = {str(i): v for i, v in enumerate(matches, 1)}
    print(display_credentials(mapping))
    value = input("Your choice ? ")
    return mapping[value]["login"]["password"]


def select_match(matches):
    try:
        return select_single_match(matches)
    except ValueError:
        return select_from_multiple_matches(matches)


def encode(payload):
    return base64.b64encode(json.dumps(payload).encode("utf-8"))


def get_session(environ):
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


def get_password(service, username):
    session = get_session(os.environ)

    # Making sure we're up to date
    bw("sync", session=session)

    results = bw("list", "items", "--url", service, session=session)

    credentials = json.loads(results)

    matches = list(match_credentials(credentials, username))

    return select_match(matches)


def set_password(service, username, password):
    session = get_session(os.environ)

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


def confirm_delete(session, credential):

    print("The following match will be DELETED:")
    print(display_credential(credential))
    if input("Confirm ? (type 'yes')").lower() == "yes":
        bw("delete", "item", credential["id"], session=session)
        print("Deleted.")
        return
    print("Cancelled.")


def delete_password(service, username):
    session = get_session(os.environ)

    bw("sync", session=session)

    result = bw("get", "item", service, session=session)

    credential = json.loads(result)

    confirm_delete(session, credential)


class BitwardenBackend(backend.KeyringBackend):
    @properties.ClassProperty
    @classmethod
    def priority(cls):
        if not bitwarden_cli_installed():
            raise RuntimeError(
                "Requires bitwarden cli: https://help.bitwarden.com/article/cli/"
            )

        return PRIORITY

    def get_password(self, service, username):
        return get_password(service, username)

    def set_password(self, service, username, password):
        return set_password(service, username, password)

    def delete_password(self, service, username):
        return delete_password(service, username)
