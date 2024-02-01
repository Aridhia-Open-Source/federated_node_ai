import os
import requests
from base64 import b64encode
from app.helpers.db import db

from app.exceptions import AuthenticationError, KeycloakError

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak")
REALM = os.getenv("KEYCLOAK_REALM", "FederatedNode")
KEYCLOAK_CLIENT = os.getenv("KEYCLOAK_CLIENT", "global")
KEYCLOAK_SECRET = os.getenv("KEYCLOAK_SECRET")
KEYCLOAK_ADMIN = os.getenv("KEYCLOAK_ADMIN")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
URLS = {
    "get_token": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
    "validate": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token/introspect",
    "client_id": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId=",
    "get_policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy?permission=false",
    "policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy",
    "scopes": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/scope?permission=false",
    "resource": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/resource",
    "permission": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/permission/scope",
    "permissions_check": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy/evaluate"
}


class Keycloak:
    def __init__(self, client='global') -> None:
        self.client_name = client
        self.admin_token = self.get_admin_token()
        self.client_id = self.get_client_id()

    @classmethod
    def get_token_from_headers(cls, header):
        return header['Authorization'].replace('Bearer ', '')

    def get_token(self, username=None, password=None, token_type='refresh_token', payload=None) -> str:
        """
        Get a token for a given set of credentials
        """
        if payload is None:
            payload = {
                'client_id': KEYCLOAK_CLIENT,
                'client_secret': KEYCLOAK_SECRET,
                'grant_type': 'password',
                'username': username,
                'password': password
            }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response_auth = requests.post(
            URLS["get_token"],
            data=payload,
            headers=headers
        )
        if response_auth.ok:
            return response_auth.json()[token_type]
        raise AuthenticationError("Failed to login")


    def get_admin_token(self):
        payload = {
            'client_id': 'admin-cli',
            'grant_type': 'password',
            'username': KEYCLOAK_ADMIN,
            'password': KEYCLOAK_ADMIN_PASSWORD
        }
        return self.get_token(token_type='access_token', payload=payload)

    def is_token_valid(self, token:str, scope:str, resource:str) -> bool:
        """
        Ping KC to check if the token is valid or not
        """
        response_auth = requests.post(
            URLS["get_token"],
            data={
                "client_secret": KEYCLOAK_SECRET,
                "client_id": KEYCLOAK_CLIENT,
                "grant_type": 'refresh_token',
                "refresh_token": token
            },
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )

        return response_auth.ok and self.check_permissions(token, scope, resource)

    def decode_token(self, token:str) -> dict:
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


    def get_client_id(self):
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        client_id_resp = requests.get(
            URLS["client_id"] + self.client_name,
            headers=headers
        )
        if not client_id_resp.ok:
            raise AuthenticationError("Could not check client")

        return client_id_resp.json()[0]["id"]


    def check_permissions(self, token:str, scope:str, resource:str) -> bool:
        access_token = self.get_token(
            payload={
                "grant_type": "refresh_token",
                "refresh_token": token,
                "client_id": self.client_name,
                "client_secret": KEYCLOAK_SECRET,
            },
            token_type='access_token'
        )
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        request_perm = requests.post(
            URLS["get_token"],
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                "audience": self.client_name,
                "response_mode": "decision",
                "permission": f"{self.get_resource(resource)["_id"]}#{scope}"
            },
            headers=headers
        )
        if not request_perm.ok:
            raise AuthenticationError("User is not authorized")
        return True

    def get_resource(self, resource_name:str) -> dict:
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        response_res = requests.get(
            (URLS["resource"] % self.client_id) + f"?name={resource_name}",
            headers=headers
        )
        if not response_res.ok:
            raise KeycloakError("Failed to fetch the resource")
        return response_res.json()[0]


    def get_policy(self, name:str, client_name='global'):
        """
        Given a name and (optional) reosource (global or dataset specific)
        return a policy dict
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        policy_response = requests.get(
            (URLS["get_policies"] % self.client_id) + f'&name={name}',
            headers=headers
        )
        if not policy_response.ok:
            raise KeycloakError("Error when fetching the policies from Keycloak")

        return policy_response.json()[0]

    def get_scope(self, name:str, client_name='global'):
        """
        Given a name and (optional) reosource (global or dataset specific)
        return a policy dict
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        policy_response = requests.get(
            (URLS["scopes"] % self.client_id) + f'&name={name}',
            headers=headers
        )
        if not policy_response.ok:
            raise KeycloakError("Error when fetching the scioes from Keycloak")

        return policy_response.json()[0]

    def create_policy(self, payload:dict, policy_type:str, client_name='global'):
        """
        Creates a custom policy for a resource
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        policy_response = requests.post(
            (URLS["policies"] % self.client_id) + policy_type,
            json=payload,
            headers=headers
        )
        if not policy_response.ok and policy_response.status_code != 409:
            raise KeycloakError("Failed to create a policy for the dataset")

        return policy_response.json()

    def create_resource(self, payload:dict, client_name='global'):
        headers={
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }

        payload["owner"] = {
            "id": self.client_id, "name": client_name
        }
        resource_response = requests.post(
            URLS["resource"] % self.client_id,
            json=payload,
            headers=headers
        )
        if not resource_response.ok:
            raise KeycloakError("Failed to create a resource for the dataset")

        return resource_response.json()

    def create_permission(self, payload:dict, client_name='global'):
        headers={
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }

        permission_response = requests.post(
            URLS["permission"] % self.client_id,
            json=payload,
            headers=headers
        )
        if not permission_response.ok and permission_response.status_code != 409:
            raise KeycloakError("Failed to create permissions for the dataset")

        return permission_response.json()
