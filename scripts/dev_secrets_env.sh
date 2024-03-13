#!/bin/bash

###
# This script is for local development purposes.
# It aims to automate the port exposure of keycloak and db internal
# and sets the KEYCLOAK_SECRET and KEYCLOAK_ADMIN_PASSWORD in the
# dev.env file. This can be used to run the webserver with the debugger.
#
# Optional arg: .env file location. Defaults to <project>/webserver/dev.env
###

DEV_ENV_FILE=webserver/dev.env
if [[ -n $1 ]]; then
    DEV_ENV_FILE=$1
fi

PASS=$(kubectl get secret -n keycloak kc-secrets -o json | jq -r '.data.KEYCLOAK_ADMIN_PASSWORD' | base64 -d)
SEC=$(kubectl get secret -n keycloak kc-secrets -o json | jq -r '.data.KEYCLOAK_GLOBAL_CLIENT_SECRET' | base64 -d)

if grep 'KEYCLOAK_SECRET=' "$DEV_ENV_FILE"; then
    sed -i -n "s/KEYCLOAK_SECRET=.*/KEYCLOAK_SECRET=${SEC}/" "$DEV_ENV_FILE"
else
    echo "KEYCLOAK_SECRET=${SEC}" >> "$DEV_ENV_FILE"
fi

if grep 'KEYCLOAK_ADMIN_PASSWORD=' "$DEV_ENV_FILE"; then
    echo "KEYCLOAK_ADMIN_PASSWORD=${PASS}" >> "$DEV_ENV_FILE"
else
    sed -i -n "s/KEYCLOAK_ADMIN_PASSWORD=.*/KEYCLOAK_ADMIN_PASSWORD=${PASS}/" "$DEV_ENV_FILE"
fi

echo "run kubectl port-forward -n keycloak svc/keycloak 8080"
echo "and kubectl port-forward svc/db 5432"
