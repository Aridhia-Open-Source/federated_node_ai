import json
import pytest
from app.models.datasets import Datasets


@pytest.fixture(scope='function')
def task_body():
    return {
        "title": "Test Task",
        "docker_image": "example:latest",
        "requested_by": "das9908-as098080c-9a80s9",
        "description": "First task ever!",
        "use_query": "SELECT * FROM patients LIMIT 10;"
    }

def test_get_list_tasks(
        client,
        simple_admin_header
    ):
    """
    Tests that admin users can see the list of tasks
    """
    response = client.get(
        '/tasks/',
        headers=simple_admin_header
    )
    assert response.status_code == 200

def test_get_list_tasks_base_user(
        client,
        simple_user_header
    ):
    """
    Tests that non-admin users cannot see the list of tasks
    """
    response = client.get(
        '/tasks/',
        headers=simple_user_header
    )
    assert response.status_code == 401

def test_create_task(
        docker_client,
        post_json_admin_header,
        query_validator,
        dataset,
        client,
        task_body
    ):
    """
    Tests task creation returns 201
    """
    data = task_body
    data["dataset_id"] = dataset.id

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 201

def test_create_task_with_non_existing_dataset(
        docker_client,
        post_json_admin_header,
        user_uuid,
        query_validator,
        client,
        task_body
    ):
    """
    Tests task creation returns 404 when the requested dataset doesn't exist
    """
    data = task_body
    data["dataset_id"] = '123456'

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 404
    assert response.json == {"error": "Dataset with id 123456 does not exist"}

def test_create_unauthorized_task(
        docker_client,
        post_json_user_header,
        dataset,
        query_validator,
        client,
        task_body
    ):
    """
    Tests task creation returns 201
    """
    data = task_body
    data["dataset_id"] = dataset.id

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_user_header
    )
    assert response.status_code == 401

def test_create_task_image_not_found(
        docker_client_404,
        post_json_admin_header,
        dataset,
        query_validator,
        client,
        task_body
    ):
    """
    Tests task creation returns 500 with a requested docker image is not found
    """
    data = task_body
    data["dataset_id"] = dataset.id

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 500
    assert response.json == {"error": "An error occurred with the Task"}

def test_create_task_with_invalid_query(
        post_json_admin_header,
        dataset,
        query_invalidator,
        client,
        task_body
    ):
    """
    Tests task creation return 500 with an invalid query
    """
    data = task_body
    data["dataset_id"] = dataset.id
    data["use_query"] = "Not a real query"

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 500

def test_cancel_task(
        client,
        docker_client,
        dataset,
        simple_admin_header,
        post_json_admin_header,
        task_body,
        query_validator
    ):
    """
    Test that an admin can cancel an existing task
    """
    data = task_body
    data["dataset_id"] = dataset.id

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 201

    response = client.post(
        f'/tasks/{response.json['task_id']}/cancel',
        headers=simple_admin_header
    )
    assert response.status_code == 201

def test_cancel_404_task(
        client,
        simple_admin_header
    ):
    """
    Test that an admin can cancel a non-existing task returns a 404
    """
    response = client.post(
        '/tasks/123456/cancel',
        headers=simple_admin_header
    )
    assert response.status_code == 404

def test_validate_task(
        client,
        simple_admin_header
    ):
    """
    Test the validation endpoint can be used by admins returns 201
    """
    response = client.post(
        '/tasks/validate',
        headers=simple_admin_header
    )
    assert response.status_code == 200

def test_validate_task_basic_user(
        client,
        simple_user_header
    ):
    """
    Test the validation endpoint can be used by non-admins returns 201
    """
    response = client.post(
        '/tasks/validate',
        headers=simple_user_header
    )
    assert response.status_code == 200
