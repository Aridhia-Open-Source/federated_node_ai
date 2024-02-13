import pytest
import json
import requests
import os
from datetime import datetime as dt, timedelta
from app.models.requests import Requests
from app.helpers.keycloak import Keycloak

@pytest.fixture
def request_base_body():
    return {
        "title": "Test Task",
        "project_name": "project1",
        "requested_by": { "email": "test@test.com" },
        "description": "First task ever!",
        "proj_start": dt.now().date().strftime("%Y-%m-%d"),
        "proj_end": (dt.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
    }

def create_request(client, body:dict, header:dict, status_code=201):
    """
    Common function to handle a request and check for a status_code
    """
    response = client.post(
        "/requests/",
        data=json.dumps(body),
        headers=header
    )
    assert response.status_code == status_code, response.data.decode()
    return response.json

def approve_request(client, req_id:str, header:dict, status_code=201):
    """
    Common function to send an approve request.
    """
    response = client.post(
        f"/requests/{req_id}/approve",
        headers=header
    )
    assert response.status_code == status_code, response.data.decode()
    return response.json

def test_can_list_requests(
        client,
        simple_admin_header
):
    """
    Tests for admin user being able to see the list of open requests
    """
    response = client.get('/requests/?status=pending', headers=simple_admin_header)
    assert response.status_code == 200

def test_cannot_list_requests(
        client,
        simple_user_header
):
    """
    Tests for non-admin user not being able to see the list of open requests
    """
    response = client.get('/requests/?status=pending', headers=simple_user_header)
    assert response.status_code == 401

def test_create_request_and_approve_is_successful(
        request_base_body,
        post_json_admin_header,
        simple_admin_header,
        dataset,
        client
    ):
    """
    Test the whole process:
        - submit request
        - approve it
        - check for few keycloak resources
        - check access to endpoints
        - delete KC client
    """
    request_base_body["dataset_id"] = dataset.id

    response_req = create_request(client, request_base_body, post_json_admin_header)
    req_id = response_req['request_id']

    response_approval = approve_request(client, req_id, simple_admin_header)
    kc_client = Keycloak(f"Request {request_base_body["requested_by"]["email"]} - {request_base_body["project_name"]}")
    assert kc_client.get_resource(f"{dataset.id}-{dataset.name}") is not None

    response_ds = client.get(
        f"/datasets/{dataset.id}",
        headers={
            "Authorization": f"Bearer {response_approval["token"]}",
            "project_name": request_base_body["project_name"]
        }
    )
    assert response_ds.status_code == 200

    # Cleanup
    requests.delete(
        f'{os.getenv("KEYCLOAK_URL")}/admin/realms/FederatedNode/clients/{kc_client.client_id}',
        headers={"Authorization": f"Bearer {kc_client.admin_token}"}
    )

def test_create_request_non_admin_is_not_successful(
        request_base_body,
        post_json_user_header,
        dataset,
        client
    ):
    """
    /requests POST returns 401 when an unauthorized user requests it
    """
    request_base_body["dataset_id"] = dataset.id
    create_request(client, request_base_body, post_json_user_header, 401)

def test_create_request_with_same_project_is_successful(
        request_base_body,
        post_json_admin_header,
        simple_admin_header,
        dataset,
        dataset2,
        client
    ):
    """
    Test the whole process:
        - submit request
        - approve it
        - submit request with same project
        - approve it
        - delete KC clients
    """
    request_base_body["dataset_id"] = dataset.id
    response_req = create_request(client, request_base_body, post_json_admin_header)
    req_id = response_req['request_id']

    approve_request(client, req_id, simple_admin_header)
    kc_client = Keycloak(f"Request {request_base_body["requested_by"]["email"]} - {request_base_body["project_name"]}")
    assert kc_client.get_resource(f"{dataset.id}-{dataset.name}") is not None

    # Second request
    request_base_body["dataset_id"] = dataset2.id
    response_req = create_request(client, request_base_body, post_json_admin_header)
    req_id = response_req['request_id']

    approve_request(client, req_id, simple_admin_header)
    kc_client2 = Keycloak(f"Request {request_base_body["requested_by"]["email"]} - {request_base_body["project_name"]}")
    assert kc_client2.get_resource(f"{dataset2.id}-{dataset2.name}") is not None

    # Cleanup
    for cl_id in [kc_client, kc_client2]:
        requests.delete(
            f'{os.getenv("KEYCLOAK_URL")}/admin/realms/FederatedNode/clients/{cl_id.client_id}',
            headers={"Authorization": f"Bearer {cl_id.admin_token}"}
        )

def test_request_for_invalid_dataset_fails(
        request_base_body,
        post_json_admin_header,
        client,
        k8s_client,
        k8s_config
    ):
    """
    /requests POST with non-existent dataset would return a 404
    """
    request_base_body["dataset_id"] = 100
    response = create_request(client, request_base_body, post_json_admin_header, 404)

    assert response == {"error": "Dataset with id 100 does not exist"}
    assert Requests.get_all() == []
