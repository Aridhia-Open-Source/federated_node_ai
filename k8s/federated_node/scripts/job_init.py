import requests
from requests import Response
import json
import os
import time

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak.keycloak.svc.cluster.local:8080")
REALM = 'master'
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "FederatedNode")
KEYCLOAK_CLIENT = os.getenv("KEYCLOAK_CLIENT", "global")
KEYCLOAK_USER = os.getenv("KEYCLOAK_ADMIN")
KEYCLOAK_PASS = os.getenv("KEYCLOAK_ADMIN_PASSWORD")

def is_response_good(response:Response):
  if not response.ok and response.status_code != 409:
    print(f"{response.status_code} - {response.text}")
    exit(1)

print("Health check on keycloak pod before starting")
for i in range(1, 5):
    print(f"Health check {i}/5")
    try:
      hc_resp = requests.get(f"{KEYCLOAK_URL}/realms/master")
      if hc_resp.ok:
          break
    except requests.exceptions.ConnectionError:
        pass
    print("Health check failed...retrying in 10 seconds")
    time.sleep(10)
if i == 5:
    print("Keycloak cannot be reached")
    exit(1)

print(f"Accessing to keycloak {REALM} realm")


payload = {
    'client_id': 'admin-cli',
    'grant_type': 'password',
    'username': KEYCLOAK_USER,
    'password': KEYCLOAK_PASS
}
headers = {
  'Content-Type': 'application/x-www-form-urlencoded'
}

response = requests.post(
    f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
    headers=headers,
    data=payload
)
is_response_good(response)
admin_token = response.json()["access_token"]

print("Got the token...Creating user in new Realm")
payload = json.dumps({
  "firstName": "Admin",
  "lastName": "Admin",
  "email": "",
  "enabled": "true",
  "username": KEYCLOAK_USER,
  "credentials": [
    {
      "type": "password",
      "temporary": False,
      "value": KEYCLOAK_PASS
    }
  ]
})
headers = {
  'Cache-Control': 'no-cache',
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {admin_token}'
}

response = requests.post(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
  headers=headers,
  data=payload
)
is_response_good(response)


print("Getting realms roles id")
headers = {
  'Authorization': f'Bearer {admin_token}'
}

response = requests.get(
    f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles",
    headers=headers
)
is_response_good(response)
role_id = [role for role in response.json() if role["name"] == "Super Administrator"][0]["id"]
print("Got realm")

headers = {
  'Cache-Control': 'no-cache',
  'Authorization': f'Bearer {admin_token}'
}

response = requests.get(
    f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users?username={KEYCLOAK_USER}",
    headers=headers
)
is_response_good(response)
user_id = response.json()[0]["id"]

print("Assigning role to user")

payload = json.dumps([
  {
    "id": role_id,
    "name": "Super Administrator"
  }
])
headers = {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {admin_token}'
}

response = requests.post(
    f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
    headers=headers,
    data=payload
)
is_response_good(response)


print("Setting up the token exchange for global client")
all_clients = requests.get(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients",
  headers = {
    'Authorization': f'Bearer {admin_token}'
  }
)
is_response_good(all_clients)
all_clients = all_clients.json()
client_id = list(filter(lambda x: x["clientId"] == 'global', all_clients))[0]['id']
rm_client_id = list(filter(lambda x: x["clientId"] == 'realm-management', all_clients))[0]['id']

client_permission_resp = requests.put(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{client_id}/management/permissions",
  json={"enabled": True},
  headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {admin_token}'
  }
)
if not client_permission_resp.ok:
    print(client_permission_resp.text)
    exit(1)

# Fetching the token exchange scope
client_te_scope_resp = requests.get(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{rm_client_id}/authz/resource-server/scope?permission=false&name=token-exchange",
  headers = {
    'Authorization': f'Bearer {admin_token}'
  }
)
is_response_good(client_te_scope_resp)
token_exch_scope = client_te_scope_resp.json()[0]["id"]

# Fetching the global resource reference in the realm-management client
resource_scope_resp = requests.get(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{rm_client_id}/authz/resource-server/resource?name=client.resource.{client_id}",
  headers = {
    'Authorization': f'Bearer {admin_token}'
  }
)
is_response_good(resource_scope_resp)
resource_id = resource_scope_resp.json()[0]["_id"]

# Creating the client policy
global_client_policy_resp = requests.post(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{rm_client_id}/authz/resource-server/policy/client",
  json={
    "name": "token-exchange-global",
    "logic": "POSITIVE",
    "clients": [client_id]
  },
  headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {admin_token}'
  }
)
if global_client_policy_resp.status_code == 409:
  global_client_policy_resp = requests.get(
    f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{rm_client_id}/authz/resource-server/policy/client?name=token-exchange-global",
    headers = {
      'Authorization': f'Bearer {admin_token}'
    }
  )
elif not global_client_policy_resp.ok:
    print(global_client_policy_resp.text)
    exit(1)
global_policy_id = global_client_policy_resp.json()[0]["id"]

# Creating the permission
client_permission_resp = requests.put(
  f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{rm_client_id}/authz/resource-server/permission/scope/13bf9ef0-412c-4da4-a3cb-9e8694adc8f9",
  json={
      "name": f"token-exchange.permission.client.{client_id}",
      "logic": "POSITIVE",
      "decisionStrategy": "UNANIMOUS",
      "resources": [resource_id],
      "policies": [global_policy_id],
      "scopes": [token_exch_scope]
  },
  headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {admin_token}'
  }
)
is_response_good(client_permission_resp)

print("Done!")
exit(0)
