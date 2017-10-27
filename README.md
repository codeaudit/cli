# RiseML Command Line Client

This is the command-line client for RiseML.

## Installation

The latest version is available for download as a single binary (provided via pyInstaller).

For Linux:
```bash
wget https://cdn.riseml.com/releases/latest/linux/riseml
```

For macOS:
```bash
wget https://cdn.riseml.com/releases/latest/osx/riseml
```

Make the file executable and move the binary in to your PATH:
```bash
chmod a+x riseml
sudo mv riseml /usr/local/bin/riseml
```

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
