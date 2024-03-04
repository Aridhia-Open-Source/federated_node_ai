import json
import pytest
from kubernetes.client.exceptions import ApiException
from unittest import mock
from unittest.mock import Mock
from app.helpers.exceptions import InvalidRequest
from app.models.tasks import Task
from tests.helpers.kubernetes import MockKubernetesClient


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
        acr_client,
        k8s_client_task,
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
        acr_client,
        post_json_admin_header,
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
        acr_client,
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
        acr_client_404,
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
    assert response.json == {"error": f"Image {task_body["docker_image"]} not found on our repository"}

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
        acr_client,
        dataset,
        k8s_client_task,
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
        task_body,
        dataset,
        acr_client,
        query_validator,
        post_json_admin_header
    ):
    """
    Test the validation endpoint can be used by admins returns 201
    """
    data = task_body
    data["dataset_id"] = dataset.id
    response = client.post(
        '/tasks/validate',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 200

def test_validate_task_basic_user(
        client,
        task_body,
        dataset,
        acr_client,
        query_validator,
        post_json_user_header
    ):
    """
    Test the validation endpoint can be used by non-admins returns 201
    """
    data = task_body
    data["dataset_id"] = dataset.id
    response = client.post(
        '/tasks/validate',
        data=json.dumps(data),
        headers=post_json_user_header
    )
    assert response.status_code == 200

def test_command_parser(
        task_body,
        dataset,
        query_validator,
        acr_client,
        mocker,
        client
):
    """
    Tests that the command passed as arg from the validate
    and run method of Task class returns a correct list of str
    """

    data = task_body
    data["dataset_id"] = dataset.id
    data["command"] = "R -e \"2+2; 3+3\""
    mocker.patch(
        'app.models.tasks.Keycloak',
        return_value=Mock()
    )
    task = Task.validate(data)
    cmd_parsed = Task(**task)._parse_command(data["command"])
    assert cmd_parsed == ["R", "-e", "2+2; 3+3"]

def test_docker_image_regex(
        task_body,
        dataset,
        query_validator,
        acr_client,
        mocker,
        client
):
    """
    Tests that the docker image is in an expected format
        <namespace?/image>:<tag>
    """

    data = task_body
    data["dataset_id"] = dataset.id
    valid_image_formats = [
        "image:3.21",
        "namespace/image:3.21",
        "namespace/image:3.21-alpha"
    ]
    invalid_image_formats = [
        "not_valid/",
        "/not-valid:",
        "/not-valid:2.31",
        "image",
        "namespace//image:3.21",
        "/image"
    ]
    mocker.patch(
        'app.models.tasks.Keycloak',
        return_value=Mock()
    )
    for im_format in valid_image_formats:
        data["docker_image"] = im_format
        Task.validate(data)

    for im_format in invalid_image_formats:
        data["docker_image"] = im_format
        with pytest.raises(InvalidRequest):
            Task.validate(data)

def test_get_results(
    acr_client,
    post_json_admin_header,
    simple_admin_header,
    query_validator,
    dataset,
    client,
    task_body,
    mocker
):
    """
    A simple test with mocked PVs to test a successful result
    fetch
    """
    # Create a new task
    data = task_body
    data["dataset_id"] = dataset.id
    # The mock has to be done manually rather than use the fixture
    # as it complains about the return value of the list_pod method
    mocker.patch(
        'app.models.tasks.KubernetesClient',
        return_value=MockKubernetesClient()
    )
    mocker.patch('app.models.tasks.uuid4', return_value="1dc6c6d1-417f-409a-8f85-cb9d20f7c741")
    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 201

    # Get results
    mocker.patch(
        'app.models.tasks.KubernetesBatchClient'
    )
    k8s_client = mocker.patch(
        'app.models.tasks.KubernetesClient',
        return_value=Mock(list_namespaced_pod=Mock())
    )
    pod_mock = Mock()
    pod_mock.metadata.labels = {"job-name": "result-job-1dc6c6d1-417f-409a-8f85-cb9d20f7c741"}
    k8s_client.return_value.list_namespaced_pod.return_value.items = [pod_mock]

    response = client.get(
        f'/tasks/{response.json["task_id"]}/results',
        headers=simple_admin_header
    )
    assert response.status_code == 200
    assert response.content_type == "application/x-tar"

def test_get_results_job_creation_failure(
    acr_client,
    post_json_admin_header,
    simple_admin_header,
    query_validator,
    dataset,
    client,
    task_body,
    mocker
):
    """
    Tests that the job creation to fetch results from a PV returns a 500
    error code
    """
    # Create a new task
    data = task_body
    data["dataset_id"] = dataset.id
    # The mock has to be done manually rather than use the fixture
    # as it complains about the return value of the list_pod method
    mocker.patch(
        'app.models.tasks.KubernetesClient',
        return_value=MockKubernetesClient()
    )
    response = client.post(
        '/tasks/',
        data=json.dumps(data),
        headers=post_json_admin_header
    )
    assert response.status_code == 201

    # Get results - creating a job fails
    k8s_batch = mocker.patch('app.models.tasks.KubernetesBatchClient')
    k8s_batch.return_value.create_namespaced_job.side_effect = ApiException(status=500, reason="Something went wrong")

    response = client.get(
        f'/tasks/{response.json["task_id"]}/results',
        headers=simple_admin_header
    )
    assert response.status_code == 500
    assert response.json["error"] == 'Failed to run pod: Something went wrong'
