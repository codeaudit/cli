# RiseML Client

## Setup

```
git clone https://github.com/riseml/client
# optionally
cd client && git checkout demo && cd ..
pip install -e client
```

## Create config environment file
Put this contents into `client.env` file to export these vars, when using riseml client.

```
# develop settings
export RISEML_API_ENDPOINT=http://localhost:3000
export RISEML_SYNC_ENDPOINT=rsync://192.168.99.100:31876/sync
export RISEML_GIT_ENDPOINT=http://192.168.99.100:31888
export RISEML_APIKEY=admin_key
```

## Check setup

Check connection to API, run:

```
riseml whoami

# should output something like this:
_admin (0b687763-0757-11e7-875b-80e65006b9ce)
```

## Deploy repository

```
mkdir test-deploy && cd test-deploy
```

Add `riseml.yml` to test-deploy dir:

```yml
project: test-deploy
train:
  kind: train
  image:
    name: ubuntu:16.10
  gpus: 0
  run: date +%s
```

Run train job:

```
riseml run -s train 
```