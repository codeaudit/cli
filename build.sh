#!/bin/bash

if [ "$1" ]; then
    url=$1
else
    url=https://api.riseml.com/spec
fi

swagger-codegen generate -i $url -l python -o . -t templates/ -c swagger-codegen.json
