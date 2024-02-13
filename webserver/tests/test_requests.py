import pytest
import json
import requests
import os
from datetime import datetime as dt, timedelta
from app.models.datasets import Datasets
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
        user_uuid,
        client,
        k8s_client,
        k8s_config
    ):
    """
    Test the whole process:
        - submit request
        - approve it
        - check for few keycloak resources
        - check access to endpoints
        - delete KC client
    """
    dataset = Datasets(name="DSRequest", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    request_base_body["dataset_id"] = dataset.id

    response = client.post(
        "/requests/",
        data=json.dumps(request_base_body),
        headers=post_json_admin_header
    )
    assert response.status_code == 201, response.data.decode()

    req_id = response.json['request_id']
    response = client.post(
        f"/requests/{req_id}/approve",
        headers=simple_admin_header
    )
    assert response.status_code == 201, response.data.decode()
    kc_client = Keycloak(f"Request {request_base_body["requested_by"]["email"]} - {request_base_body["project_name"]}")
    assert kc_client.get_resource(f"{dataset.id}-{dataset.name}") is not None

    response_ds = client.get(
        f"/datasets/{dataset.id}",
        headers={
            "Authorization": f"Bearer {response.json["token"]}",
            "project_name": request_base_body["project_name"]
        }
    )
    assert response_ds.status_code == 200

    # Cleanup
    requests.delete(
        f'{os.getenv("KEYCLOAK_URL")}/admin/realms/FederatedNode/clients/{kc_client.client_id}',
        headers={"Authorization": f"Bearer {kc_client.admin_token}"}
    )

def test_request_non_admin_is_not_successful(
        request_base_body,
        post_json_user_header,
        basic_user,
        client,
        k8s_client,
        k8s_config
    ):
    """
    /requests POST returns 401 when an unauthorized user requests it
    """
    dataset = Datasets(name="DSRequest", host="example.com", password='pass', username='user')
    dataset.add(user_id=basic_user["id"])
    request_base_body["dataset_id"] = dataset.id

    response = client.post(
        "/requests/",
        data=json.dumps(request_base_body),
        headers=post_json_user_header
    )
    assert response.status_code == 401, response.data.decode()

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
    response = client.post(
        "/requests/",
        data=json.dumps(request_base_body),
        headers=post_json_admin_header
    )
    assert response.status_code == 404
    assert response.json == {"error": "Dataset with id 100 does not exist"}
    assert Requests.get_all() == []
