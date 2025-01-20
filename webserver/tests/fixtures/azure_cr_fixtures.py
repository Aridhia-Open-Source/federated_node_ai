import pytest
from unittest.mock import Mock

from app.helpers.container_registries import AzureRegistry
from app.models.container import Container
from app.models.registry import Registry


@pytest.fixture
def azure_cr_name():
    return "acr.azurecr.io"

@pytest.fixture
def az_registry_client(mocker):
    mocker.patch(
        'app.models.registry.AzureRegistry',
        return_value=Mock()
    )

@pytest.fixture
def azure_cr_client(mocker):
    return mocker.patch(
        'app.helpers.container_registries.AzureRegistry',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=True)
        )
    )

@pytest.fixture
def azure_cr_client_404(mocker):
    mocker.patch(
        'app.models.registry.AzureRegistry',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=False)
        )
    )

@pytest.fixture
def az_cr_class(mocker, azure_cr_name, ):
    return AzureRegistry(azure_cr_name, creds={"user": "", "token": ""})

@pytest.fixture
def registry_az(client, k8s_client, azure_cr_name) -> Registry:
    reg = Registry(azure_cr_name, '', '')
    reg.add()
    return reg

@pytest.fixture
def container_az(client, k8s_client, registry_az, image_name) -> Container:
    img, tag = image_name.split(':')
    cont = Container(img, registry_az, tag, True)
    cont.add()
    return cont
