#!/bin/bash

echo "Setting up docker-compose env vars"
export PGHOST=db
export PGDATABASE=test_app
export PGPORT=5432
export PGUSER=admin
export PGPASSWORD=test_app
export KEYCLOAK_URL=http://keycloak:8080
export KEYCLOAK_REALM=FederatedNode
export ACR_URL=acruksouthatdev.azurecr.io
export KEYCLOAK_SECRET=asdf12ad89123ocasASD129
export KEYCLOAK_CLIENT=global
export KEYCLOAK_ADMIN=admin
export KEYCLOAK_ADMIN_PASSWORD=password1

docker compose -f docker-compose-tests.yaml run "$1" --name flask-app-test app
docker cp flask-app-test:/app/artifacts/coverage.xml ../artifacts/

if [[ -n "$1" ]]; then
    echo "Cleaning up compose resources"
    docker compose -f docker-compose-tests.yaml stop
    docker compose -f docker-compose-tests.yaml rm -f
    docker rm flask-app-test
fi
