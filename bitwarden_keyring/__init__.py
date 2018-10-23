import base64
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from keyring import backend
from keyring.util import properties

PRIORITY = 10  # Doc is oddly vague


def get_db_location(environ, platform):
    """
    This is a port of
    https://github.com/bitwarden/cli/blob/783e7fc8348d02853983211fa28dd8448247ba92/src/bw.ts#L67-L75
    """
    env = environ.get("BITWARDENCLI_APPDATA_DIR")
    if env:
        path = os.path.expanduser(env)

    elif platform == "darwin":
        path = os.path.expanduser("~/Library/Application Support/Bitwarden CLI")

    elif platform == "win32":
        path = os.path.expandvars("%AppData%/Bitwarden CLI")

    else:
        path = os.path.expanduser("~/snap/bw/current/.config/Bitwarden CLI")
        if not os.path.exists(path):
            path = os.path.expanduser("~/.config/Bitwarden CLI")

    return os.path.join(path, "data.json")


def open_db(db_location):
    try:
        with open(db_location, "r") as file:
            return json.load(file)
    except IOError:
        return {}


def extract_logged_user(db):
    return db.get("userEmail")


def bitwarden_cli_installed():
    return bool(shutil.which("bw"))


def extract_domain_name(full_url):
    full_domain = urlsplit(full_url).netloc
    if not full_domain:
        return full_url

    return ".".join(full_domain.split(".")[-2:])


def ask_for_session(is_authenticated):
    command = ask_for_session_command(is_authenticated)
    result = bw(command, "--raw")
    return result


def ask_for_session_command(is_authenticated):
    return "unlock" if is_authenticated else "login"


def bw(*args, session=None):

    cli_args = ["bw"]
    if session:
        cli_args += ["--session", session]

    cli_args += list(args)

    result = subprocess.run(cli_args, stdout=subprocess.PIPE).stdout.strip()

    if result == b"Failed to decrypt.\nVault is locked.":
        print(
            "Wrong credentials. Maybe you left a stale BW_SESSION in the environment ?"
        )
        raise ValueError

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
        return environ["BW_SESSION"]

    location = get_db_location(environ, sys.platform)

    db = open_db(location)

    user = extract_logged_user(db)

    return ask_for_session(bool(user))


def get_password(service, username):
    session = get_session(os.environ)

    # Making sure we're up to date
    bw("sync", session=session)

    search = extract_domain_name(service)

    results = bw("list", "items", "--search", search, session=session)

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

    search = extract_domain_name(service)

    result = bw("get", "item", search, session=session)

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
