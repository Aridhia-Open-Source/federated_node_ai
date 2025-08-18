import logging
import os
import random
import re
import requests
from base64 import b64encode
from flask import request

from app.helpers.exceptions import AuthenticationError, UnauthorizedError, KeycloakError
from app.helpers.const import PASS_GENERATOR_SET

logger = logging.getLogger('keycloak_helper')
logger.setLevel(logging.INFO)

KEYCLOAK_NAMESPACE = os.getenv("KEYCLOAK_NAMESPACE")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", f"http://keycloak.{KEYCLOAK_NAMESPACE}.svc.cluster.local")
REALM = os.getenv("KEYCLOAK_REALM", "FederatedNode")
KEYCLOAK_CLIENT = os.getenv("KEYCLOAK_CLIENT", "global")
KEYCLOAK_SECRET = os.getenv("KEYCLOAK_SECRET")
KEYCLOAK_ADMIN = os.getenv("KEYCLOAK_ADMIN")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
URLS = {
    "health_check": f"{KEYCLOAK_URL}/realms/master",
    "get_token": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
    "validate": f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token/introspect",
    "client": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients",
    "client_secret": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/client-secret",
    "client_exchange": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/management/permissions",
    "client_auth": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server",
    "get_policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy?permission=false",
    "roles": f"{KEYCLOAK_URL}/admin/realms/{REALM}/roles",
    "policies": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy",
    "scopes": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/scope",
    "resource": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/resource",
    "permission": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/permission/scope",
    "permissions_check": f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/%s/authz/resource-server/policy/evaluate",
    "user": f"{KEYCLOAK_URL}/admin/realms/{REALM}/users",
    "user_role": f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/%s/role-mappings/realm",
    "user_reset": f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/%s/reset-password"
}

class Keycloak:
    def __init__(self, client='global') -> None:
        self.client_name = client
        self.admin_token = self.get_admin_token()
        self.client_id = self.get_client_id()
        self.client_secret = self._get_client_secret()

    @classmethod
    def get_token_from_headers(cls) -> str:
        """
        Public method for generalize the token fetching from an HTTP header
        """
        return request.headers['Authorization'].replace('Bearer ', '')

    def _post_json_headers(self) -> dict:
        """
        Default value for a json request header
        """
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }

    def exchange_global_token(self, token:str) -> str:
        """
        Token exchange across clients. From global to the instanced one
        """
        acpayload = {
            'client_secret': KEYCLOAK_SECRET,
            'client_id': KEYCLOAK_CLIENT,
            'grant_type': 'refresh_token',
            'refresh_token': token
        }
        ac_resp = requests.post(
            URLS["get_token"],
            data=acpayload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        if not ac_resp.ok:
            logger.info(ac_resp.content.decode())
            raise KeycloakError("Cannot get an access token")
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
            logger.info(exchange_resp.content.decode())
            raise KeycloakError("Cannot exchange token")
        return exchange_resp.json()["access_token"]

    def get_impersonation_token(self, user_id:str) -> str:
        """
        Method to request a token on behalf of another user
        : user_id : The keycloak user's id to impersonate
        """
        payload = {
            'client_secret': KEYCLOAK_SECRET, # Target client
            'client_id': KEYCLOAK_CLIENT, #Target client
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'requested_token_type': 'urn:ietf:params:oauth:token-type:refresh_token',
            'subject_token': self.get_admin_token_global(),
            'requested_subject': user_id,
            'audience': KEYCLOAK_CLIENT
        }
        exchange_resp = requests.post(
            URLS["get_token"],
            data=payload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        if not exchange_resp.ok:
            logger.info(exchange_resp.content.decode())
            raise KeycloakError("Cannot exchange impersonation token")
        return exchange_resp.json()["refresh_token"]

    def check_if_keycloak_resp_is_valid(self, response) -> bool:
        """
        If the response status code is:
            - 2xx (ok) or
            - 409 (conflict, resource already exists)
        return true, meaning we don't need to recreate them and we can continue
        """
        return response.status_code == 409 or response.ok

    def _get_client_secret(self, client_id:str=None) -> str:
        """
        Given the client id, fetches the client's secret if has one.
        """
        if not client_id:
            client_id = self.client_id

        secret_resp = requests.get(
            URLS["client_secret"] % client_id,
            headers={
                "Authorization": f"Bearer {self.admin_token}"
            }
        )
        if not secret_resp.ok:
            logger.info(secret_resp.content.decode())
            raise KeycloakError(f"Failed to fetch {client_id}'s secret")

        return secret_resp.json()["value"]

    def get_token(self, username=None, password=None, token_type='refresh_token', payload:dict=None, raise_on_temp_pass:bool=True) -> str:
        """
        Get a token for a given set of credentials

        :params token_type: one of "refresh_token" and "access_token"
        :params payload: the body for the post request to keycloak
        :params raise_on_temp_pass: if set to False, it will exit early and
            return the whole response object, otherwise it will raise exceptions
            on status code != 200
        """
        logger.info("%s) get_token", self.client_name)
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

        if not raise_on_temp_pass:
            return response_auth

        if not response_auth.ok:
            logger.info(response_auth.content.decode())

            if re.match("Account is not fully set up", response_auth.json().get("error_description")):
                raise AuthenticationError("Temporary password must be changed before logging in")

            raise AuthenticationError("Failed to login")
        return response_auth.json()[token_type]

    def is_user_admin(self, token:str) -> bool:
        """
        Given a token checks if the owner is an Admin or SuperAdmin
        """
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
        if not response_auth.ok:
            logger.info(response_auth.content.decode())
            raise AuthenticationError("Failed to login")
        return "Administrator" in response_auth.json()["realm_access"]["roles"]

    def get_admin_token_global(self) -> str:
        """
        Get administrative level token
        """
        logger.info("get_admin_token_global")
        payload = {
            'client_id': KEYCLOAK_CLIENT,
            'client_secret': KEYCLOAK_SECRET,
            'grant_type': 'password',
            'username': KEYCLOAK_ADMIN,
            'password': KEYCLOAK_ADMIN_PASSWORD
        }
        return self.get_token(token_type='access_token', payload=payload)

    def get_admin_token(self) -> str:
        """
        Get administrative level token
        """
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
        """
        Simple token decode, mostly to fetch user general info or exp date
        """
        b64_auth = b64encode(f"{self.client_name}:{self.client_secret}".encode()).decode()
        response_validate = requests.post(
            URLS["validate"],
            data=f"token={token}",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {b64_auth}'
            }
        )
        if response_validate.json().get('active'):
            return response_validate.json()
        raise AuthenticationError("Token expired. Validation failed")

    def get_client_id(self, client_name=None) -> str:
        """
        Get a give Keycloak client id, if not provided, the instanced
        one will be returned
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        if client_name is None:
            client_name = self.client_name

        client_id_resp = requests.get(
            URLS["client"],
            params = {"clientId": client_name},
            headers=headers
        )
        if not client_id_resp.ok:
            logger.info(client_id_resp.content.decode())
            raise KeycloakError("Could not find client")
        if not len(client_id_resp.json()):
            raise KeycloakError("Could not find project", 400)

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
            logger.info(request_perm.content.decode())
            raise UnauthorizedError("User is not authorized")
        return True

    def get_role(self, role_name:str) -> dict[str, str]:
        """
        Get the realm roles.

        Returns a dictionary {name: str, id: str}

        Raises a specific exception if not found
        """
        realm_resp = requests.get(
            URLS["roles"] + f"/{role_name}",
            headers={
                'Authorization': f'Bearer {self.admin_token}',
            }
        )
        match realm_resp.status_code:
            case 200:
                return realm_resp.json()
            case 404:
                logger.info(realm_resp.content.decode())
                raise KeycloakError(f"Role {role_name} does not exist", 400)
            case _:
                logger.info(realm_resp.content.decode())
                raise KeycloakError("Failed to fetch roles")

    def get_resource(self, resource_name:str) -> dict:
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        response_res = requests.get(
            URLS["resource"] % self.client_id,
            params={
                "name": resource_name
            },
            headers=headers
        )
        if not response_res.ok:
            logger.info(response_res.content.decode())
            raise KeycloakError("Failed to fetch the resource")
        if len(response_res.json()) > 0:
            return response_res.json()[0]

        raise KeycloakError("Failed to fetch the resource")

    def patch_resource(self, resource_name:str, **kwargs) -> dict:
        """
        Given a resource name submits a PUT request by using the
        current resource body merged with what's been passed trough
        kwargs.
        Most likely we're interested in:
            - name
            - displayName
        as values to be merged and patched into the current resource
        """
        resource = self.get_resource(resource_name)
        resource.update(kwargs)

        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        response_res = requests.put(
            (URLS["resource"] % self.client_id) + f"/{resource["_id"]}",
            json=resource,
            headers=headers
        )
        if not response_res.ok:
            logger.info(response_res.content.decode())
            raise KeycloakError("Failed to patch the resource")

    def get_policy(self, name:str) -> dict:
        """
        Given a name and (optional) reosource (global or dataset specific)
        return a policy dict
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        policy_response = requests.get(
            URLS["get_policies"] % self.client_id,
            params={"name": name},
            headers=headers
        )
        if not policy_response.ok:
            logger.info(policy_response.content.decode())
            raise KeycloakError("Error when fetching the policies from Keycloak")

        return policy_response.json()[0]

    def get_scope(self, name:str) -> dict:
        """
        Given a name and (optional) reosource (global or dataset specific)
        return a policy dict
        """
        headers={
            'Authorization': f'Bearer {self.admin_token}'
        }
        scope_response = requests.get(
            URLS["scopes"] % self.client_id,
            params={
                "permission": False,
                "name": name
            },
            headers=headers
        )
        if not scope_response.ok:
            logger.info(scope_response.content.decode())
            raise KeycloakError("Error when fetching the scopes from Keycloak")

        if not scope_response.json():
            raise KeycloakError("Scope not found")

        return scope_response.json()[0]

    def create_client(self, client_name:str, token_lifetime:int) -> dict:
        """
        Create a new client for a given project. If it exist already,
            return that one
        : token_lifetime : time in seconds for the
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
                    "client.offline.session.max.lifespan": token_lifetime
                }
            },
            headers=self._post_json_headers()
        )

        # Client exists. Return that one
        if not client_post_rest.ok and client_post_rest.status_code != 409:
            logger.info(client_post_rest.content.decode())
            raise KeycloakError("Failed to create a project")

        update_req = requests.put(
            URLS["client_auth"] % self.get_client_id(client_name),
            json={
                "decisionStrategy": "AFFIRMATIVE",
            },
            headers=self._post_json_headers()
        )
        if not update_req.ok:
            logger.info(update_req.content.decode())
            raise KeycloakError("Failed to create a project")

        return self.get_client_id(client_name)

    def create_scope(self, scope_name) -> dict:
        """
        Create a custom scope for the instanced client
        """
        scope_post_rest = requests.post(
            URLS["scopes"] % self.client_id,
            json={"name": scope_name},
            headers=self._post_json_headers()
        )
        if scope_post_rest.status_code == 409:
            return self.get_scope(scope_name)
        elif not scope_post_rest.ok:
            logger.info(scope_post_rest.content.decode())
            raise KeycloakError("Failed to create a project's scope")

        return scope_post_rest.json()

    def create_policy(self, payload:dict, policy_type:str) -> dict:
        """
        Creates a custom policy for a resource
        """
        policy_response = requests.post(
            (URLS["policies"] % self.client_id) + policy_type,
            json=payload,
            headers=self._post_json_headers()
        )
        # If it exists already
        if policy_response.status_code == 409:
            return self.get_policy(payload["name"])
        elif not policy_response.ok:
            logger.info(policy_response.content.decode())
            raise KeycloakError("Failed to create a project's policy")

        return policy_response.json()

    def create_or_update_time_policy(self, payload:dict, policy_type:str) -> dict:
        """
        Time policies need a separate treatement. This is the only policy that we will
        allow to be updated, in cases of token renewals via DAR
        """
        current_policy = self.create_policy(payload, policy_type)
        # Only update the time policy. If it's a brand new, it will return
        # the payload as response, otherwise the "config" field will be there
        if current_policy.get("config"):
            current_policy["config"]["noa"] = payload['notOnOrAfter']
            current_policy["config"]["nbf"] = payload['notBefore']
            policy_response = requests.put(
                (URLS["policies"] % self.client_id) + "/" + current_policy["id"],
                json=current_policy,
                headers=self._post_json_headers()
            )
            if not policy_response.ok:
                logger.info(policy_response.content.decode())
                raise KeycloakError("Failed to create a project's policy")

        return current_policy

    def create_resource(self, payload:dict, client_name='global') -> dict:
        payload["owner"] = {
            "id": self.client_id, "name": client_name
        }
        resource_response = requests.post(
            URLS["resource"] % self.client_id,
            json=payload,
            headers=self._post_json_headers()
        )
        if resource_response.status_code == 409:
            return self.get_resource(payload["name"])
        elif not resource_response.ok:
            logger.info(resource_response.content.decode())
            raise KeycloakError("Failed to create a project's resource")

        return resource_response.json()

    def create_permission(self, payload:dict) -> dict:
        permission_response = requests.post(
            URLS["permission"] % self.client_id,
            json=payload,
            headers=self._post_json_headers()
        )
        if not self.check_if_keycloak_resp_is_valid(permission_response):
            logger.info(permission_response.content.decode())
            raise KeycloakError("Failed to create a project's permission")

        return permission_response.json()

    ### USERS' section
    def create_user(self, set_temp_pass=False, **kwargs) -> dict:
        """
        Method that handles the user creation. Keycloak will need username as
        mandatory field, but we would set a temporary password so the user
        can reset it on the first login.
        **kwargs are optional parameters i.e. email, firstName, lastName, etc.
        """
        random_password = ''.join(random.choice(PASS_GENERATOR_SET) for _ in range(12))
        username = kwargs.get("username", kwargs.get("email"))

        # Make sure the role exists before creating the user
        role = self.get_role(kwargs.get("role", "Users"))

        user_response = requests.post(
            URLS["user"],
            json={
                "firstName": kwargs.get("firstName", ""),
                "lastName": kwargs.get("lastName", ""),
                "email": kwargs.get("email"),
                "enabled": True,
                "emailVerified": True,
                "username": username,
                "credentials": [{
                    "type": "password",
                    "temporary": set_temp_pass,
                    "value": random_password
                }]
            },
            headers=self._post_json_headers()
        )

        if not user_response.ok and user_response.status_code != 409:
            logger.info(user_response.text)
            raise KeycloakError("Failed to create the user")

        user_info = self.get_user(username)

        # Assign a role
        self.assign_role_to_user(user_info["id"], role)

        user_info["password"] = random_password

        return user_info

    def assign_role_to_user(self, user_id:str, role:str|dict ="Users"):
        """
        Keycloak REST API can't handle role assignation to a user on creation
        has to be a separate call.

        :param user_id: a string representing the user_id from keycloak
        :param role: either a string with the role name, or a dictionary that contains role's name and id
        """
        if isinstance(role, str):
            role = self.get_role(role)
        user_role_response = requests.post(
            URLS["user_role"] % user_id,
            json=[role],
            headers=self._post_json_headers()
        )
        if not user_role_response.ok and user_role_response.status_code != 409:
            logger.info(user_role_response.text)
            raise KeycloakError("Failed to create the user")

    def list_users(self) -> list[dict]:
        """
        Method to return a dictionary representing a Keycloak user
        """
        user_response = requests.get(
            URLS["user"],
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not user_response.ok:
            raise KeycloakError("Failed to fetch the user")

        return user_response.json()

    def get_user(self, username:str) -> dict:
        """
        Method to return a dictionary representing a Keycloak user,
        checks for both username and email
        """
        by_un = self.get_user_by_username(username)
        if by_un:
            return by_un

        by_em = self.get_user_by_email(username)
        if by_em:
            return by_em

        raise KeycloakError("Failed to fetch the created user")

    def get_user_by_id(self, user_id:str) -> dict:
        """
        Method to return a dictionary representing a Keycloak user
        """
        user_response = requests.get(
            f"{URLS["user"]}/{user_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not user_response.ok:
            raise KeycloakError("Failed to fetch the user")

        return user_response.json() if user_response.json() else None

    def get_user_by_username(self, username:str) -> dict:
        """
        Method to return a dictionary representing a Keycloak user
        """
        user_response = requests.get(
            URLS["user"],
            params= {
                "username": username,
                "exact": True
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not user_response.ok:
            raise KeycloakError("Failed to fetch the user")

        return user_response.json()[0] if user_response.json() else None

    def get_user_by_email(self, email:str) -> dict:
        """
        Method to return a dictionary representing a Keycloak user,
        using their email
        """
        user_response = requests.get(
            URLS["user"],
            params= {
                "email": email,
                "exact": True
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not user_response.ok:
            raise KeycloakError("Failed to fetch the user")

        return user_response.json()[0] if user_response.json() else None

    def get_user_role(self, user_id:str) -> list[str]:
        """
        From a user id, get all of their realm roles
        """
        role_response = requests.get(
            URLS["user_role"] % user_id,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not role_response.ok:
            raise KeycloakError("Failed to get the user's role")

        return [role["name"] for role in role_response.json()]

    def has_user_roles(self, user_id:str, roles:set) -> bool:
        """
        With the user id checks if it has certain realm roles
        """
        return roles.intersection(self.get_user_role(user_id))

    def reset_user_pass(self, user_id:str, username:str, old_pass:str, new_pass:str):
        """
        Simply change the temp password for the user.
        The old_pass will be used to check if a change is needed,
            if that's the case, we'll update the password
        """
        auth_user = self.get_token(username=username, password=old_pass, raise_on_temp_pass=False)

        if not re.match("Account is not fully set up", auth_user.json().get("error_description")):
            raise AuthenticationError(
                "Incorrect credentials"
            )

        res_pass_resp = requests.put(
            URLS["user_reset"] % user_id,
            json={
                "type": "password",
                "temporary": False,
                "value": new_pass
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        if not self.check_if_keycloak_resp_is_valid(res_pass_resp):
            logging.error(res_pass_resp.json())
            raise KeycloakError("Could not update the password.")

    def enable_token_exchange(self):
        """
        Method to automate the setup for this client to
        allow token exchange on behalf of a user for admin-level
        """
        client_permission_resp = requests.put(
            URLS["client_exchange"] % self.client_id,
            json={"enabled": True},
            headers = self._post_json_headers()
        )
        if not client_permission_resp.ok:
            raise KeycloakError("Failed to set exchange permissions")

        rm_client_id = self.get_client_id('realm-management')
        global_client_id = self.get_client_id('global')

        # Fetching the token exchange scope
        client_te_scope_resp = requests.get(
            URLS["scopes"] % rm_client_id,
            params = {
                "permission": False,
                "name": "token-exchange"
            },
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
        )
        if not client_te_scope_resp.ok:
            raise KeycloakError("Error on keycloak")

        token_exch_scope = client_te_scope_resp.json()[0]["id"]
        resource_scope_resp = requests.get(
            URLS["resource"] % rm_client_id,
            params = {
                "name": f"client.resource.{self.client_id}"
            },
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
        )
        resource_id = resource_scope_resp.json()[0]["_id"]

        # Create a custom client exchange policy
        global_client_policy_resp = requests.post(
            (URLS["policies"] % rm_client_id) + "/client",
            json={
                "name": f"token-exchange-{self.client_name}",
                "logic": "POSITIVE",
                "clients": [global_client_id, self.client_id]
            },
            headers = self._post_json_headers()
        )
        if global_client_policy_resp.status_code == 409:
            global_policy_id = requests.get(
                (URLS["policies"] % rm_client_id) + "/client",
                params = {
                    "name": f"token-exchange-{self.client_name}"
                },
                headers = self._post_json_headers()
            ).json()[0]["id"]
        elif not global_client_policy_resp.ok:
            logger.error(global_client_policy_resp.json())
            raise KeycloakError("Something went wrong in creating the set of permissions on Keycloak")
        else:
            global_policy_id = global_client_policy_resp.json()["id"]

        token_exch_name = f"token-exchange.permission.client.{self.client_id}"
        token_exch_permission_resp = requests.get(
            URLS["permission"] % rm_client_id,
            params = {
                "name": token_exch_name
            },
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
        )
        token_exch_permission_id = token_exch_permission_resp.json()[0]["id"]
        # Updating the permission
        client_permission_resp = requests.put(
            (URLS["permission"] % rm_client_id) + f"/{token_exch_permission_id}",
            json={
                "name": token_exch_name,
                "logic": "POSITIVE",
                "decisionStrategy": "UNANIMOUS",
                "resources": [resource_id],
                "policies": [global_policy_id],
                "scopes": [token_exch_scope]
            },
            headers = self._post_json_headers()
        )
        if not client_permission_resp.ok:
            raise KeycloakError("Failed to update the exchange permission")
