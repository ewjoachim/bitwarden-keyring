from keyring import backend, credentials


class BitwardenBackend(backend.KeyringBackend):
    """
    A keyring backend for Bitwarden.
    """

    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...
    def get_credential(
        self,
        service: str,
        username: str | None,
    ) -> credentials.Credential | None: ...
