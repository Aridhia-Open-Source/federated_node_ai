import pytest
from unittest.mock import Mock

from app.helpers.container_registries import GitHubRegistry
from app.models.container import Container
from app.models.registry import Registry


GH_CLASS = 'app.models.registry.GitHubClient'


@pytest.fixture
def gh_cr_name():
    return "ghcr.io/somecr"

@pytest.fixture
def gh_registry_client(mocker):
    mocker.patch(
        GH_CLASS,
        return_value=Mock()
    )

@pytest.fixture
def gh_cr_client(mocker):
    return mocker.patch(
        'app.helpers.container_registries.GitHubClient',
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=True)
        )
    )

@pytest.fixture
def gh_cr_class(mocker, gh_cr_name, ):
    return GitHubRegistry(gh_cr_name, creds={"user": "", "token": "sometoken"})

@pytest.fixture
def gh_cr_client_404(mocker):
    mocker.patch(
        GH_CLASS,
        return_value=Mock(
            login=Mock(return_value="access_token"),
            get_image_tags=Mock(return_value=False)
        )
    )

@pytest.fixture
def registry_gh(client, k8s_client, gh_cr_name) -> Registry:
    reg = Registry(gh_cr_name, '', '')
    reg.add()
    return reg

@pytest.fixture
def container_gh(client, k8s_client, registry_gh, image_name) -> Container:
    img, tag = image_name.split(':')
    cont = Container(img, registry_gh, tag, True)
    cont.add()
    return cont
