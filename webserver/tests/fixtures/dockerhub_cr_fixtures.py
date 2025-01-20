import pytest
from unittest.mock import Mock

from app.helpers.container_registries import DockerRegistry
from app.models.container import Container
from app.models.registry import Registry


DOCKER_CLASS = 'app.models.registry.DockerRegistry'

@pytest.fixture
def dockerhub_cr_name():
    return "acr.dockerhubcr.io"

@pytest.fixture
def dh_registry_client(mocker):
    mocker.patch(
        DOCKER_CLASS,
        return_value=Mock()
    )

@pytest.fixture
def dockerhub_cr_client(mocker):
    return mocker.patch(
        'app.helpers.container_registries.DockerRegistry',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=True)
        )
    )

@pytest.fixture
def dockerhub_cr_client_404(mocker):
    mocker.patch(
        DOCKER_CLASS,
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=False)
        )
    )

@pytest.fixture
def dh_cr_class(mocker, dockerhub_cr_name, ):
    return DockerRegistry(dockerhub_cr_name, creds={"user": "", "token": ""})

@pytest.fixture
def registry_dh(client, k8s_client, dockerhub_cr_name) -> Registry:
    reg = Registry(dockerhub_cr_name, '', '')
    reg.add()
    return reg

@pytest.fixture
def container_dh(client, k8s_client, registry_dh, image_name) -> Container:
    img, tag = image_name.split(':')
    cont = Container(img, registry_dh, tag, True)
    cont.add()
    return cont
