import json
import os
import pytest
<<<<<<< HEAD
import requests
import responses
=======
import docker
import requests
>>>>>>> main
from datetime import datetime as dt, timedelta
from sqlalchemy.orm.session import close_all_sessions
from unittest.mock import Mock
from app import create_app
<<<<<<< HEAD
from app.helpers.acr import ACRClient
from app.helpers.db import db
from app.helpers.kubernetes import KubernetesBatchClient
from app.models.dataset import Dataset
from app.models.request import Request
from app.helpers.keycloak import Keycloak, URLS, KEYCLOAK_SECRET, KEYCLOAK_CLIENT
from tests.helpers.kubernetes import MockKubernetesClient
=======
from app.helpers.db import db
from app.models.dataset import Dataset
from app.models.request import Request
from app.helpers.keycloak import Keycloak, URLS, KEYCLOAK_SECRET, KEYCLOAK_CLIENT
>>>>>>> main

sample_ds_body = {
    "name": "TestDs",
    "host": "db",
    "port": 5432,
    "username": "Username",
    "password": "pass",
    "catalogue": {
        "title": "test",
        "description": "test description"
    },
    "dictionaries": [{
        "table_name": "test",
        "description": "test description"
    }]
}

@pytest.fixture
def user_token(basic_user):
    """
    Since calling Keycloak.get_impersonation_token is not
    viable as there is an "audience" conflict.
    All clients are hardcoded, as only global and the DAR clients
    are allowed to exchange tokens, not admin-cli.
    """
    admin_token = Keycloak().get_token(
        username=os.getenv("KEYCLOAK_ADMIN"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),
        token_type='access_token'
    )
    payload = {
        'client_secret': KEYCLOAK_SECRET,
        'client_id': KEYCLOAK_CLIENT,
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'requested_token_type': 'urn:ietf:params:oauth:token-type:refresh_token',
        'subject_token': admin_token,
        'requested_subject': basic_user["id"],
        'audience': 'global'
    }
    exchange_resp = requests.post(
        URLS["get_token"],
        data=payload,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    )
    return exchange_resp.json()["refresh_token"]

@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield

<<<<<<< HEAD
# Users' section
=======
>>>>>>> main
@pytest.fixture
def user_uuid():
    return Keycloak().get_user(os.getenv("KEYCLOAK_ADMIN"))["id"]

@pytest.fixture
def login_admin(client):
    return Keycloak().get_token(
        username=os.getenv("KEYCLOAK_ADMIN"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    )

<<<<<<< HEAD
@pytest.fixture()
def basic_user():
    return Keycloak().create_user(**{"email": "test@basicuser.com"})

=======
>>>>>>> main
@pytest.fixture
def login_user(client, basic_user):
    return Keycloak().get_impersonation_token(basic_user["id"])

@pytest.fixture
def simple_admin_header(login_admin):
    return {"Authorization": f"Bearer {login_admin}"}

@pytest.fixture
def post_json_admin_header(login_admin):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {login_admin}"
    }

@pytest.fixture
def simple_user_header(user_token):
    return {"Authorization": f"Bearer {user_token}"}

@pytest.fixture
def post_json_user_header(user_token):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }

@pytest.fixture
def post_form_admin_header(login_admin):
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {login_admin}"
    }

<<<<<<< HEAD
# Flask client to perform requests
=======
>>>>>>> main
@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    with app.test_client() as tclient:
        with app.app_context():
            db.create_all()
            yield tclient
            close_all_sessions()
            db.drop_all()

<<<<<<< HEAD
# K8s
@pytest.fixture
def k8s_config(mocker):
    mocker.patch('kubernetes.config.load_kube_config', return_value=Mock())

    mocker.patch(
        'app.helpers.kubernetes.config',
        side_effect=Mock()
    )

@pytest.fixture()
def k8s_client(mocker, k8s_config):
    mocker.patch(
        'kubernetes.client.CoreV1Api',
        return_value=MockKubernetesClient()
    )
    mocker.patch(
        'kubernetes.client.BatchV1Api',
        return_value=KubernetesBatchClient()
    )

@pytest.fixture()
def k8s_client_task(mocker, k8s_config):
    return mocker.patch(
        'app.models.task.KubernetesClient',
        return_value=MockKubernetesClient()
    )

# Query validators
@pytest.fixture(scope="function", autouse=False)
def query_validator(mocker):
    mocker.patch(
        'app.models.task.validate_query',
=======
@pytest.fixture()
def k8s_config(mocker):
    mock = Mock()
    mocker.patch('kubernetes.config.load_kube_config', return_value=mock)
    return mock

@pytest.fixture()
def k8s_client(mocker):
    mock = Mock()
    mocker.patch(
        'kubernetes.client.CoreV1Api',
        return_value=Mock(
            read_namespaced_secret=Mock(return_value=Mock(data={'PGUSER': 'YWJjMTIz', 'PGPASSWORD': 'YWJjMTIz'}))
        )
    )
    return mock

@pytest.fixture(scope="function", autouse=False)
def query_validator(mocker):
    mocker.patch(
        'app.tasks_api.validate_query',
>>>>>>> main
        return_value=True,
        autospec=True
    )

@pytest.fixture(scope="function", autouse=False)
def query_invalidator(mocker):
    mocker.patch(
<<<<<<< HEAD
        'app.models.task.validate_query',
=======
        'app.tasks_api.validate_query',
>>>>>>> main
        return_value=False,
        autospec=True
    )

<<<<<<< HEAD
# ACR mocking
@pytest.fixture()
def acr_client(mocker):
    mocker.patch(
        'app.models.task.ACRClient',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            has_image_metadata=Mock(return_value=True)
        )
    )

@pytest.fixture()
def acr_http(mocker):
    rsps = responses.RequestsMock()
    # with responses.RequestsMock() as rsps:
    # Mock the request in the order they are submitted.
    # Unfortunately the match param doesn't detect form data
    url = os.getenv("ACR_URL")
    image = "example"
    rsps.add(
        responses.GET,
        f"https://{url}/oauth2/token?service={url}&scope=repository:{image}:metadata_read",
        status=200
    )
    rsps.add(
        responses.GET,
        f"https://{url}/v2/{image}/tags/list",
        status=200
    )
    return rsps

@pytest.fixture()
def acr_client_404(mocker):
    mocker.patch(
        'app.models.task.ACRClient',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            has_image_metadata=Mock(return_value=False)
        )
    )

@pytest.fixture()
def acr_class():
    return ACRClient(
        os.getenv("ACR_URL"),
        os.getenv("ACR_USERNAME"),
        os.getenv("ACR_PASSWORD"),
    )

# Dataset Mocking
=======
@pytest.fixture()
def docker_client(mocker):
    mocker.patch(
        'docker.from_env',
        return_value=Mock(
            login=Mock(),
            images=Mock(
                get_registry_data=Mock()
            )
        ),
        autospec=True
    )

@pytest.fixture()
def docker_client_404(mocker):
    mocker.patch(
        'docker.from_env',
        return_value=Mock(
            login=Mock(),
            images=Mock(
                get_registry_data=Mock(
                    side_effect=docker.errors.NotFound("image not found")
                )
            )
        ),
        autospec=True
    )

@pytest.fixture()
def basic_user():
    return Keycloak().create_user(**{"email": "test@basicuser.com"})

>>>>>>> main
@pytest.fixture(scope='function')
def dataset_post_body():
    return {
        "name": "TestDs",
        "host": "db",
        "port": 5432,
        "username": "Username",
        "password": "pass",
        "catalogue": {
            "title": "test",
            "description": "test description"
        },
        "dictionaries": [{
            "table_name": "test",
            "description": "test description"
        }]
    }

@pytest.fixture
<<<<<<< HEAD
def dataset(client, user_uuid, k8s_client):
=======
def dataset(client, user_uuid, k8s_client, k8s_config):
>>>>>>> main
    dataset = Dataset(name="TestDs", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    return dataset

@pytest.fixture
<<<<<<< HEAD
def dataset2(client, user_uuid, k8s_client):
=======
def dataset2(client, user_uuid, k8s_client, k8s_config):
>>>>>>> main
    dataset = Dataset(name="AnotherDS", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    return dataset

@pytest.fixture
<<<<<<< HEAD
def access_request(client, dataset, user_uuid, k8s_client):
=======
def access_request(client, dataset, user_uuid, k8s_client, k8s_config):
>>>>>>> main
    request = Request(
        title="TestRequest",
        project_name="example.com",
        requested_by=json.dumps({"email": "some@test.com"}),
        dataset=dataset,
        proj_start=dt.now().date().strftime("%Y-%m-%d"),
        proj_end=(dt.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
    )
    request.add()
    return request
<<<<<<< HEAD

# Conditional url side_effects
def side_effect(dict_mock:dict):
    """
    This tries to mock dynamically according to what urllib3.requests
    receives as args returning a default 200 response body with an empty body

    :param dict_mock: should include the following keys
        - url:str       (required): portion of the requested url to mock
        - method:str    (optional): request method, defaults to GET
        - status:int    (optional): response status_code, defaults to 200
        - body:bytes    (optional): response body, defaults to an empty bytes string
    """
    def _url_side_effects(*args, **kwargs):
        """
        args:
        [0] -> method
        [1] -> url
        """
        default_body = ''.encode()
        method, url = args
        if dict_mock['url'] in url and dict_mock.get('method', 'GET') == method:
            return Mock(
                status=dict_mock.get('status', 200), data=dict_mock.get('body', default_body)
            )
        return Mock(
            status=200, data=default_body
        )
    return _url_side_effects
=======
>>>>>>> main
