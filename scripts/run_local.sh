#!/bin/bash
set -e
export CLUSTER_NAME=federatednode
echo "Starting MK"
minikube start -p $CLUSTER_NAME --driver=docker

echo "Switching context"
kubectl config use-context $CLUSTER_NAME

echo "applying definitions"
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/

echo "If new images are needed, load them up with:"
echo "minikube -p $CLUSTER_NAME image load <image_name>"
