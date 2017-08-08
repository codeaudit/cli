# RiseML Client

## Setup

```
git clone https://github.com/riseml/client
pip install -e client --process-dependency-links
```

## Environment settings
```
# develop settings
export RISEML_APIKEY=admin_key
export RISEML_SYNC_ENDPOINT=rsync://192.168.99.100:31876/sync
export RISEML_ENDPOINT=http://localhost:80
```

## Check setup

Check connection to API, run:

```
riseml whoami

# should output something like this:
admin (0b687763-0757-11e7-875b-80e65006b9ce)
```

## Deploy repository

```
mkdir test-deploy && cd test-deploy
```

Add `riseml.yml` to test-deploy dir:

```yml
project: test-deploy
train:
  image:
    name: ubuntu:16.10
  framework: tensorflow
  tensorflow:
    distributed: false
    tensorboard: 'true'
  run:
    - echo hello
  resources:
    cpus: 1
    mem: 1024
    gpus: 0
```

Run train job:

```
riseml train 
```

## Build a standalone bundle

PyInstaller currently not supporting python3.6, so use py3.4 or py3.5 executable.

```bash
virtualenv env -p python3.4 && source env/bin/activate
pip3 install pyinstaller
git clone https://github.com/riseml/client
pip3 install -e client --process-dependency-links
pyinstaller client/riseml/__main__.py --onefile --name riseml 
```