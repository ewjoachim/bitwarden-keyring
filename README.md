# Bitwarden Keyring

[![Build Status](https://travis-ci.org/ewjoachim/bitwarden-keyring.svg?branch=master)](https://travis-ci.org/ewjoachim/bitwarden-keyring)

Implementation of the [Keyring](https://pypi.org/project/keyring/) backend code reading secrets from [Bitwarden](https://bitwarden.com) using [Bitwarden-cli](https://help.bitwarden.com/article/cli/)

## Overview

The [Keyring](https://pypi.org/project/keyring/) python package provides a handy single point of entry for any secret holding system, allowing for seemless integration of those systems into applications needing secrets, like [twine]().

This projects implement Keyring to be able to read secrets from Bitwarden, an open source multiplatform cloud/self-hostable password manager.

This backend assumes that it will be used in the context of a CLI application, and that it can communicate with the user using `sdtin`, `stdout` and `stderr`. We could implement an additional backend for use in a library assuming that everything is already unlocked, or another one using `pinentry` to ask the user.

## Requirements

This project uses the official [bitwarden CLI](https://help.bitwarden.com/article/cli/) under the hood, because there's no simple official Python bitwarden lib. Here are the installation instructions as of October 2018 and the link to the [up to date instructions](https://github.com/bitwarden/cli#downloadinstall)

You can install the Bitwarden CLI multiple different ways:

**NPM**

If you already have the Node.js runtime installed on your system, you can install the CLI using NPM. NPM makes it easy to keep your installation updated and should be the preferred installation method if you are already using Node.js.

```bash
npm install -g @bitwarden/cli
```

**Native Executable**

Natively packaged versions of the CLI are provided for each platform which have no requirements on installing the Node.js runtime. You can obtain these from the [downloads section](https://help.bitwarden.com/article/cli/#download--install) in the Bitwarden documentation.

**Other Package Managers**

- [Chocolatey](https://chocolatey.org/packages/bitwarden-cli)
  ```powershell
  choco install bitwarden-cli
  ```
- [Homebrew](https://formulae.brew.sh/formula/bitwarden-cli)
  ```bash
  brew install bitwarden-cli
  ```
- [Snap](https://snapcraft.io/bw)
  ```bash
  sudo snap install bw
  ```

## Installation and configuration

```
pip install bitwarden-keyring
```

then run
```
python -m bitwarden_keyring install
```

The Python packaging ecosystem can be quite a mess.

[![XKCD 1987: Python Environment. The Python environmental protection agency wants to seal it in a cement chamber, with pictorial messages to future civilizations warning them about the danger of using sudo to install random Python packages.](https://imgs.xkcd.com/comics/python_environment_2x.png)](https://xkcd.com/1987/)

Because of this, it's likely that your setup and my setup are nothing alike. Keyring [supports](https://pypi.org/project/keyring/#config-file-content) a configuration option allowing to explicitely define the path to a backend. You may need that for your installation, or maybe not.

## Licensing

`bitwarden-keyring` is published under the terms of the [MIT License](LICENSE.md).
The name Bitwarden is most probably the property of 8bit Solutions LLC.


## Contributions and Code of Conduct

Contributions are welcome, please refer to the [Contributing](CONTRIBUTING.md) guide.
Please keep in mind that all interactions with the project are required to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
