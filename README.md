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
export RISEML_CLUSTER_ID=?
export RISEML_ENVIRONMENT=?
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

```bash
git clone https://github.com/riseml/client
cd client
virtualenv env && source env/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller riseml.spec
```
