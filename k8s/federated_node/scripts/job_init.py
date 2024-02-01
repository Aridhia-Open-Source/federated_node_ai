import requests
import json
import os
import time

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak.keycloak.svc.cluster.local:8080")
REALM = 'master'
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "FederatedNode")
KEYCLOAK_CLIENT = os.getenv("KEYCLOAK_CLIENT", "global")
KEYCLOAK_USER = os.getenv("KEYCLOAK_ADMIN")
KEYCLOAK_PASS = os.getenv("KEYCLOAK_ADMIN_PASSWORD")

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

url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"

payload = {
    'client_id': 'admin-cli',
    'grant_type': 'password',
    'username': KEYCLOAK_USER,
    'password': KEYCLOAK_PASS
}
headers = {
  'Content-Type': 'application/x-www-form-urlencoded'
}

response = requests.request("POST", url, headers=headers, data=payload)
if not response.ok:
    print(response.text)
    exit(1)
admin_token = response.json()["access_token"]


print("Got the token...Creating user in new Realm")

url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
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

response = requests.request("POST", url, headers=headers, data=payload)
if not response.ok:
    print(response.text)
    exit(1)



print("Getting realms roles id")
url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles"

headers = {
  'Authorization': f'Bearer {admin_token}'
}

response = requests.request("GET", url, headers=headers)
if not response.ok:
    print(response.text)
    exit(1)
role_id = [role for role in response.json() if role["name"] == "Super Administrator"][0]["id"]
print("Got realm")


url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users?username={KEYCLOAK_USER}"

payload = {}
headers = {
  'Cache-Control': 'no-cache',
  'Authorization': f'Bearer {admin_token}'
}

response = requests.request("GET", url, headers=headers, data=payload)
if not response.ok:
    print(response.text)
    exit(1)
user_id = response.json()[0]["id"]


print("Assigning role to user")
url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm"

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

response = requests.request("POST", url, headers=headers, data=payload)
if not response.ok:
    print(response.text)
    exit(1)

print("Done!")
exit(0)
