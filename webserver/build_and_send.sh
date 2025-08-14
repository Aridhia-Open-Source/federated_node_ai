#!/bin/bash

set -e

make build_docker

microk8s ctr image rm ghcr.io/aridhia-open-source/federated_node_run:1.3.0-slm
docker save ghcr.io/aridhia-open-source/federated_node_run:1.3.0-slm > fn.tar
microk8s ctr image import fn.tar
rm fn.tar
kubectl rollout restart -n qcfederatednode deployment backend
