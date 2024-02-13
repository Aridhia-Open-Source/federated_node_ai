#!/bin/bash

echo "Setting up docker-compose env vars"
export PGHOST=db
export PGDATABASE=test_app
export PGPORT=5432
export PGUSER=admin
export PGPASSWORD=test_app
export KEYCLOAK_URL=http://keycloak:8080
export KEYCLOAK_REALM=FederatedNode
export ACR_URL=test.acrio.com
export KEYCLOAK_SECRET=asdf12ad89123ocasASD129
export KEYCLOAK_CLIENT=global
export KEYCLOAK_ADMIN=admin
export KEYCLOAK_ADMIN_PASSWORD=password1

is_ci=$1

echo "Starting docker compose"
if [[ "$is_ci" != "ci" ]]; then
    docker compose -f docker-compose-tests.yaml run --rm app
else
    docker compose -f docker-compose-tests.yaml run --name flask-app-test app
    exit_code=$?
    docker cp flask-app-test:/app/artifacts/coverage.xml ../artifacts/
    echo "Cleaning up compose resources"
    docker compose -f docker-compose-tests.yaml stop
    docker compose -f docker-compose-tests.yaml rm -f
    docker rm flask-app-test
    exit $exit_code
fi
