## Statement

PRs are welcome, I (@ewjoachim) will try to provide mentorship and guidance to anyone who asks.
This projects supports diversity and all contributors are required to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Tests

Tests are written with pytest, and with a high coverage. Please make sure to separate
IOs when possible and to mock as little as possible.
We're still lacking proper integration tests with a bitwarden in a docker.

## Development workflow

This project uses uv and prek.

### Create a local environment

```console
uv sync
```

Use `uv sync --python=3.x` to work against a specific Python version.

### Run code quality tools

```console
# Run once:
uvx prek run --all-files

# Install pre-commit hooks:
uvx prek install
```

### Run tests

```console
uv run pytest
```

### Release process

Create a GitHub Release. The publish workflow is triggered from tags and handles the
package release to PyPI.
