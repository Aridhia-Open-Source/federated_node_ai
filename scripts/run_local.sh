#!/bin/bash
set -e
export CLUSTER_NAME=federatednode
echo "Starting MK"
minikube start -p $CLUSTER_NAME --driver=docker

echo "Switching context"
kubectl config use-context $CLUSTER_NAME

echo "applying definitions"

HELM_CHART_NAME=federatednode
INSTALLED_VERSION=$(helm list --filter "^$HELM_CHART_NAME" -o json | jq -r .[].chart)

if [[ -z "$INSTALLED_VERSION" ]]; then
    echo "Applying helm chart"
    helm install $HELM_CHART_NAME k8s/federated_node
else
    echo "Upgrading installed helm chart"
    helm upgrade $HELM_CHART_NAME k8s/federated_node
fi

echo "If new images are needed, load them up with:"
echo "minikube -p $CLUSTER_NAME image load <image_name>"
