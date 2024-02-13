import os
import pytest
import docker
import requests
from sqlalchemy import select
from sqlalchemy.orm.session import close_all_sessions
from unittest.mock import Mock
from app import create_app
from app.helpers.db import db
from app.models.datasets import Datasets
from app.helpers.keycloak import Keycloak, URLS, KEYCLOAK_SECRET, KEYCLOAK_CLIENT

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

@pytest.fixture
def user_uuid():
    return Keycloak().get_user(os.getenv("KEYCLOAK_ADMIN"))["id"]

@pytest.fixture
def login_admin(client):
    return Keycloak().get_token(
        username=os.getenv("KEYCLOAK_ADMIN"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    )

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
        return_value=True,
        autospec=True
    )

@pytest.fixture(scope="function", autouse=False)
def query_invalidator(mocker):
    mocker.patch(
        'app.tasks_api.validate_query',
        return_value=False,
        autospec=True
    )

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
def dataset(client, user_uuid, k8s_client, k8s_config):
    dataset = Datasets(name="TestDs", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    return dataset

@pytest.fixture
def dataset2(client, user_uuid, k8s_client, k8s_config):
    dataset = Datasets(name="AnotherDS", host="example.com", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    return dataset
