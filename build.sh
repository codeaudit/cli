#!/bin/bash

if [ "$1" ]; then
    url=$1
else
    url=https://api.riseml.com/spec
fi

swagger-codegen generate -i $url -l python -o tmp -t templates/ -c swagger-codegen.json

rm -rf riseml/client
mv tmp/riseml riseml/client
mv tmp/setup.py .

rm tmp/README.md
rm tmp/.gitignore
rm tmp/git_push.sh
rmdir tmp
