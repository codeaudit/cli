[![Build Status](https://travis-ci.org/riseml/cli.svg?branch=master)](https://travis-ci.org/riseml/cli)

# RiseML Command Line Client

This is the command-line client for RiseML, which allows you to run and manage experiments.

## Installation

The latest version can be downloaded and installed as a single binary by executing the following command:

```bash
bash -c "$(curl -fsSL https://get.riseml.com/install-cli)"
```

Follow the script's instructions and add `~/.riseml/bin` to your PATH if you're not installing it globally.

To download RiseML manually (e.g., because you need a specific version), follow our detailed [installation instructions](INSTALL.md).

See our [release notes](RELEASES.md) for a list of recent changes and how to upgrade from previous versions.

## Development

The client is written for Python3.

Follow these steps to create a virtual environment with the client:

```bash
virtualenv venv -p python3
source ./venv/bin/activate
git clone https://github.com/riseml/client
pip install -e client
pip install -r client/requirements.txt
```
The client will be available via `riseml-dev` in the virtual environment!

### Build a standalone bundle

```bash
git clone https://github.com/riseml/client
cd client
virtualenv env && source env/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller riseml.spec
```

## Configuration

The client stores its configuration in the file `$HOME/.riseml/config`.
The syntax is similar to the kubeconfig file of kubectl.
