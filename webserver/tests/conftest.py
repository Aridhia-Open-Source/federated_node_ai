import pytest
from app import create_app
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.helpers.db import Base, build_sql_uri

# class BasePyTest:
#     def setup_class():
#         engine = create_engine(build_sql_uri())
#         Base.metadata.create_all(engine)
#         session = Session()

#     def teardown_class():
#         session.rollback()
#         session.close()

@pytest.fixture(scope='session')
def app():
    app = create_app()
    app.config.update({
        "TESTING": True
    })
    ctx = app.app_context()
    ctx.push()
    engine = create_engine(build_sql_uri())
    Base.metadata.create_all(engine)
    session = Session()
    yield app
    # clean up / reset resources here
    ctx.pop()
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

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
