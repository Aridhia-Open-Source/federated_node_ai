#!/bin/bash

set -e

docker build \
  -f build/helm-unittest/Dockerfile . -t helm-unittest-fn

docker run --name helm-test helm-unittest-fn
exit_code=$?

docker rm helm-test

exit $exit_code
