import json
import pytest
from sqlalchemy import select
from unittest import mock
from unittest.mock import Mock, MagicMock
from app.models.datasets import Datasets
from app.models.tasks import Tasks


@pytest.fixture(scope='function')
def task_body():
    return {
        "title": "Test Task",
        "docker_image": "example:latest",
        "requested_by": "das9908-as098080c-9a80s9",
        "description": "First task ever!",
        "use_query": "SELECT * FROM patients LIMIT 10;"
    }

def test_create_task(post_json_admin_header, user_uuid, query_validator, client, task_body, k8s_client, k8s_config):
    """
    Tests task creation returns 201
    """
    dataset = Datasets(name="TestDs", host="db_host", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    data = task_body
    data["dataset_id"] = dataset.id

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 201

# This for some reason still persists the mocking of app.helpers.query_validator.validate
def test_create_task_with_invalid_query(post_json_admin_header, user_uuid, query_invalidator, client, task_body, k8s_client, k8s_config):
    """
    Tests task creation returns 201
    """
    dataset = Datasets(name="TestDs", host="db_host", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    data = task_body
    data["dataset_id"] = dataset.id
    data["use_query"] = "Not a real query"

    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 500
