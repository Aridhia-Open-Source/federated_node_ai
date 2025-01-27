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

push_chart:
	curl --request POST \
		--form 'chart=@artifacts/federated-node-${VERSION}.tgz' \
		--user r-casula:${HELM_TOKEN} \
		https://gitlab.com/api/v4/projects/aridhia%2Ffederated-node/packages/helm/api/develop/charts

build_keycloak:
	docker build build/keycloak -f build/keycloak/keycloak.Dockerfile -t ghcr.io/aridhia-open-source/federated_keycloak:0.0.1
