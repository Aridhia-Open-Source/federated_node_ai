import os
import requests
from base64 import b64encode
from flask import current_app
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
    "client": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients",
    "client_id": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId=",
    "client_secret": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/client-secret",
    "client_auth": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server",
    "get_policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy?permission=false",
    "roles": f"{KEYCLOAK_URL}/admin/realms/{REALM}/roles",
    "policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy",
    "scopes": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/scope",
    "resource": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/resource",
    "permission": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/permission/scope",
    "permissions_check": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy/evaluate"
}


class Keycloak:
    def __init__(self, client='global') -> None:
        self.client_secret = KEYCLOAK_SECRET
        self.client_name = client
        self.admin_token = self.get_admin_token()
        self.client_id = self.get_client_id()
        self.client_secret = self._get_client_secret()

    @classmethod
    def get_token_from_headers(cls, header):
        return header['Authorization'].replace('Bearer ', '')

    def exchange_global_token(self, token:str):
        acpayload = {
            'client_secret': KEYCLOAK_SECRET,
            'client_id': KEYCLOAK_CLIENT,
            'grant_type': 'refresh_token',
            'refresh_token': token,
        }
        ac_resp = requests.post(
            URLS["get_token"],
            data=acpayload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        if not ac_resp.ok:
            current_app.logger.warn(ac_resp.content.decode())
            raise KeycloakError("Cannot exchange token")
        access_token = ac_resp.json()["access_token"]
        payload = {
            'client_secret': KEYCLOAK_SECRET,
            'client_id': KEYCLOAK_CLIENT,
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token',
            'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token',
            'subject_token': access_token,
            'audience': self.client_name
        }
        exchange_resp = requests.post(
            URLS["get_token"],
            data=payload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        if not exchange_resp.ok:
            current_app.logger.warn(exchange_resp.content.decode())
            raise KeycloakError("Can't exchange token")
        return exchange_resp.json()["access_token"]

    def check_if_keycloak_resp_is_valid(self, response):
        """
        If the response status code is:
            - 2xx (ok) or
            - 409 (conflict, resource already exists)
        return true, meaning we don't need to recreate them and we can continue
        """
        return response.status_code == 409 or response.ok

    def _get_client_secret(self):
        """
        Given the client id, fetches the client's secret if has one.
        """
        secret_resp = requests.get(
            URLS["client_secret"] % self.client_id,
            headers={
                "Authorization": f"Bearer {self.admin_token}"
            }
        )
        if not secret_resp.ok:
            current_app.logger.warn(secret_resp.content.decode())
            raise KeycloakError("Failed to fetch client's secret")
        return secret_resp.json()["value"]

    def get_token(self, username=None, password=None, token_type='refresh_token', payload=None) -> str:
        """
        Get a token for a given set of credentials
        """
        if payload is None:
            payload = {
                'client_id': self.client_name,
                'client_secret': self.client_secret,
                'grant_type': 'password',
                'username': username,
                'password': password
            }

        response_auth = requests.post(
            URLS["get_token"],
            data=payload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        if not response_auth.ok:
            current_app.logger.warn(response_auth.content.decode())
            raise AuthenticationError("Failed to login")
        return response_auth.json()[token_type]


    def get_admin_token(self):
        payload = {
            'client_id': 'admin-cli',
            'grant_type': 'password',
            'username': KEYCLOAK_ADMIN,
            'password': KEYCLOAK_ADMIN_PASSWORD
        }
        return self.get_token(token_type='access_token', payload=payload)

    def is_token_valid(self, token:str, scope:str, resource:str, tok_type='refresh_token') -> bool:
        """
        Ping KC to check if the token is valid or not
        """
        is_access_token = tok_type == 'access_token'
        if is_access_token:
            response_auth = requests.post(
                URLS["validate"],
                data={
                    "client_secret": self.client_secret,
                    "client_id": self.client_name,
                    "token": token
                },
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
        else:
            response_auth = requests.post(
                URLS["get_token"],
                data={
                    "client_secret": self.client_secret,
                    "client_id": self.client_name,
                    "grant_type": tok_type,
                    tok_type: token
                },
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

        return response_auth.ok and self.check_permissions(token, scope, resource, is_access_token)

    def decode_token(self, token:str) -> dict:
        b64_auth = b64encode(f"{self.client_name}:{self.client_secret}".encode()).decode()
        response_cert = requests.post(
            URLS["validate"],
            data=f"token={token}",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {b64_auth}'
            }
        )
        return response_cert.json()

    def get_client_id(self, client_name=None):
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        if client_name is None:
            client_name = self.client_name

        client_id_resp = requests.get(
            URLS["client_id"] + client_name,
            headers=headers
        )
        if not client_id_resp.ok:
            current_app.logger.warn(client_id_resp.content.decode())
            raise AuthenticationError("Could not check client")

        return client_id_resp.json()[0]["id"]

    def check_permissions(self, token:str, scope:str, resource:str, is_access_token=False) -> bool:
        if not is_access_token:
            token = self.get_token(
                payload={
                    "grant_type": "refresh_token",
                    "refresh_token": token,
                    "client_id": self.client_name,
                    "client_secret": self.client_secret,
                },
                token_type='access_token'
            )
        headers={
            'Authorization': f'Bearer {token}',
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
            current_app.logger.warn(request_perm.content.decode())
            raise AuthenticationError("User is not authorized")
        return True

    def get_role(self, role_name:str):
        """
        Get the realm roles
        """
        realm_resp = requests.get(
            URLS["roles"] + f"?search={role_name}",
            headers={
                'Authorization': f'Bearer {self.admin_token}',
            }
        )
        if not realm_resp.ok:
            current_app.logger.warn(realm_resp.content.decode())
            raise KeycloakError("Failed to fetch roles")
        return realm_resp.json()[0]

    def get_resource(self, resource_name:str) -> dict:
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        response_res = requests.get(
            (URLS["resource"] % self.client_id) + f"?name={resource_name}",
            headers=headers
        )
        if not response_res.ok:
            current_app.logger.warn(response_res.content.decode())
            raise KeycloakError("Failed to fetch the resource")
        return response_res.json()[0]


    def get_policy(self, name:str):
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
            current_app.logger.warn(policy_response.content.decode())
            raise KeycloakError("Error when fetching the policies from Keycloak")

        return policy_response.json()[0]

    def get_scope(self, name:str):
        """
        Given a name and (optional) reosource (global or dataset specific)
        return a policy dict
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        scope_response = requests.get(
            (URLS["scopes"] % self.client_id) + f'?permission=false&name={name}',
            headers=headers
        )
        if not scope_response.ok:
            current_app.logger.warn(scope_response.content.decode())
            raise KeycloakError("Error when fetching the scioes from Keycloak")

        return scope_response.json()[0]

    def create_client(self, client_name:str):
        """
        Create a new client for a given project
        """
        client_post_rest = requests.post(
            URLS['client'],
            json={
                "clientId": client_name,
                "authorizationServicesEnabled": True,
                "directAccessGrantsEnabled": True,
                "serviceAccountsEnabled": True,
                "publicClient": False,
                "redirectUris": ["/"],
                "attributes": {
                    "client.offline.session.max.lifespan": 60 * 60 * 24 * 30 * 12
                }
            },
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
        )
        if client_post_rest.status_code == 409:
            return self.get_client_id(client_name)
        elif not client_post_rest.ok:
            current_app.logger.warn(client_post_rest.content.decode())
            raise KeycloakError("Failed to create a project")

        edit_client_resp = requests.put(
            URLS["client_auth"] % self.get_client_id(client_name),
            json={
                "decisionStrategy": "AFFIRMATIVE",
            },
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
        )

        return client_post_rest.json()

    def create_scope(self, scope_name):
        """
        Create a custom scope for the instanced client
        """
        scope_post_rest = requests.post(
            URLS["scopes"] % self.client_id,
            json={"name": scope_name},
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
        )
        if scope_post_rest.status_code == 409:
            return self.get_scope(scope_name)
        elif not scope_post_rest.ok:
            current_app.logger.warn(scope_post_rest.content.decode())
            raise KeycloakError("Failed to setup a project")

        return scope_post_rest.json()

    def create_policy(self, payload:dict, policy_type:str):
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
        if policy_response.status_code == 409:
            return self.get_policy(payload["name"])
        elif not policy_response.ok:
            current_app.logger.warn(policy_response.content.decode())
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
        if resource_response.status_code == 409:
            return self.get_resource(payload["name"])
        elif not resource_response.ok:
            current_app.logger.warn(resource_response.content.decode())
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
        if not self.check_if_keycloak_resp_is_valid(permission_response):
            current_app.logger.warn(permission_response.content.decode())
            raise KeycloakError("Failed to create permissions for the dataset")

        return permission_response.json()
