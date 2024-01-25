import pytest
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
def client():
    app = create_app()
    app.testing = True
    with app.test_client() as tclient:
        with app.app_context():
            db.create_all()
            yield tclient
            db.session.close_all()
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
            # read_namespaced_secret=Mock(return_value=Mock(data={'token': b'YWJjMTIz'}))
        )
    )
    return mock

@pytest.fixture(scope='function')
def dataset_post_body():
    return sample_ds_body
