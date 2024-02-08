import json
from app.models.datasets import Datasets
from app.models.requests import Requests


def test_request_is_successful(post_json_admin_header, user_uuid, client, k8s_client, k8s_config):
    """
    /requests POST
    """
    dataset = Datasets(name="DSRequest", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    response = client.post(
        "/requests/",
        data=json.dumps({
            "title": "Test Task",
            "project_name": "project1",
            "requested_by": { "email": "test@test.com" },
            "description": "First task ever!",
            "proj_start": "2024-01-01",
            "proj_end": "2024-02-01",
            "dataset_id": dataset.id
        }),
        headers=post_json_admin_header
    )
    assert response.status_code == 201, response.data.decode()
    assert list(response.json.keys()) == ['request_id']

def test_request_for_invalid_dataset_fails(post_json_admin_header, client, k8s_client, k8s_config):
    """
    /requests POST with non-existent dataset would return a 404
    """
    response = client.post(
        "/requests/",
        data=json.dumps({
            "title": "Test Task",
            "project_name": "project1",
            "requested_by": "das9908-as098080c-9a80s9",
            "description": "First task ever!",
            "proj_start": "2024-01-01",
            "proj_end": "2024-02-01",
            "dataset_id": 100
        }),
        headers=post_json_admin_header
    )
    assert response.status_code == 404
    assert response.json == {"error": "Dataset with id 100 does not exist"}
    assert Requests.get_all() == []
