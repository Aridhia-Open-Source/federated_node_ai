SHELL=/bin/bash

hadolint:
	./scripts/run_hadolint.sh

run_local:
	./scripts/run_local.sh

expose_api:
	minikube -p federatednode service backend --url

dashboard:
	minikube -p federatednode dashboard --url --port 41234

pylint:
	./scripts/pylint.sh

chart:
	helm package k8s/federated-node -d artifacts/

helm_tests:
	docker build -f build/helm-unittest/Dockerfile . -t helm-unittest-fn
	docker run --name helm-test helm-unittest-fn
	docker rm helm-test

build_keycloak:
	docker build build/keycloak -f build/keycloak/keycloak.Dockerfile -t ghcr.io/aridhia-open-source/federated_keycloak:0.0.1
