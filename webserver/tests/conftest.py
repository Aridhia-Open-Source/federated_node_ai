import pytest
from sqlalchemy.orm.session import close_all_sessions
from unittest.mock import Mock
from app import create_app
from app.helpers.db import db

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
def app_ctx(app):
    with app.app_context():
        yield

@pytest.fixture
def user_uuid():
    return '1234-a213a2-785cde2'

@pytest.fixture
def good_tokens(user_uuid, mocker):
    mocker.patch(
        'app.helpers.keycloak.is_token_valid',
        return_value = True,
        autospec=True
    )
    mocker.patch(
        'app.helpers.keycloak.decode_token',
        return_value = {
            'sub': user_uuid
        },
        autospec=True
    )


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
        'app.helpers.query_validator.validate',
        return_value = True,
        autospec=True
    )

@pytest.fixture(scope="function", autouse=False)
def query_invalidator(mocker):
    mocker.patch(
        'app.helpers.query_validator.validate',
        return_value = False,
        autospec=True
    )

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
