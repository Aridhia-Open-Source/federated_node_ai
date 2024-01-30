from functools import wraps
from flask import request
import json
import os
import requests
from base64 import b64encode

from app.exceptions import AuthenticationError

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak")
REALM = os.getenv("KEYCLOAK_REALM", "FederatedNode")
KEYCLOAK_CLIENT = os.getenv("KEYCLOAK_CLIENT", "global")
KEYCLOAK_SECRET = os.getenv("KEYCLOAK_SECRET")
KEYCLOAK_ADMIN = os.getenv("KEYCLOAK_ADMIN")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
URLS = {
    "get_token": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
    "validate": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token/introspect",
    "client_id": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={KEYCLOAK_CLIENT}",
    "permissions": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy/evaluate"
}


def get_token(username:str, password:str, token_type='refresh_token', payload=None) -> str:
    """
    Get a token for a given set of credentials
    """
    if payload is None:
        payload = f'client_id={KEYCLOAK_CLIENT}&client_secret={KEYCLOAK_SECRET}&grant_type=password&username={username}&password={password}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response_auth = requests.post(
        URLS["get_token"],
        data=payload,
        headers=headers
    )
    if response_auth.status_code == 200:
        return response_auth.json()[token_type]
    raise AuthenticationError("Failed to login")


def get_admin_token():
    payload = f'client_id=admin-cli&grant_type=password&username={KEYCLOAK_ADMIN}&password={KEYCLOAK_ADMIN_PASSWORD}'
    return get_token(KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD, 'access_token', payload)

def auth(scope='public'):
    def auth_wrapper(func):
        @wraps(func)
        def _auth(*args, **kwargs):
            try:
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
            except KeyError:
                raise AuthenticationError("Token not provided")

            if is_token_valid(token, scope):
                return func(*args, **kwargs)
            else:
                raise AuthenticationError("Token is expired or not valid")
        return _auth
    return auth_wrapper

def is_token_valid(token:str, scope:str) -> bool:
    """
    Ping KC to check if the token is valid or not
    """
    payload = f'client_secret={KEYCLOAK_SECRET}&client_id={KEYCLOAK_CLIENT}&grant_type=refresh_token&refresh_token={token}'
    response_auth = requests.post(
        URLS["get_token"],
        data=payload,
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    )

    return response_auth.status_code == 200 and check_permissions(token, scope)

def decode_token(token:str) -> dict:
    b64_auth = b64encode(f"{KEYCLOAK_CLIENT}:{KEYCLOAK_SECRET}".encode()).decode()
    response_cert = requests.post(
        URLS["validate"],
        data=f"token={token}",
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {b64_auth}'
        }
    )
    return response_cert.json()


def check_permissions(token:str, scope:str) -> bool:
    headers={
        'Authorization': f'Bearer {get_admin_token()}'
    }
    client_id_resp = requests.get(
        URLS["client_id"],
        headers=headers
    )
    if not client_id_resp.ok:
        raise AuthenticationError("Could not check token")

    client_id = client_id_resp.json()[0]["id"]
    import jwt
    user_info = jwt.decode(token,options={"verify_signature": False})
    headers['Content-Type'] = 'application/json'
    payload = json.dumps({
        "resources": [{
            "scopes": [
                "admin"
            ]}
        ],
        "userId": user_info['sub'],
        "entitlements": True
    })
    request = requests.post(
        URLS["permissions"] % client_id,
        data=payload,
        headers=headers
    )
    if not request.ok:
        raise AuthenticationError("Could not check permissions")
    return request.json()["results"][0]["status"] == 'PERMIT'
