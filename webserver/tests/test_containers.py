from copy import deepcopy
import pytest
from unittest.mock import Mock

from app.helpers.exceptions import InvalidRequest
from app.models.container import Container
from tests.fixtures.azure_cr_fixtures import *


@pytest.fixture(scope='function')
def container_body(registry):
    return deepcopy({
        "name": "",
        "registry": registry.url,
        "tag": "1.2.3",
        "ml": True
    })


class TestContainers:
    def test_docker_image_regex(
        self,
        container_body,
        cr_client,
        registry_client,
        mocker,
        client
    ):
        """
        Tests that the docker image is in an expected format
            <namespace?/image>:<tag>
        """
        valid_image_formats = [
            {"name": "image", "tag": "3.21"},
            {"name": "namespace/image", "tag": "3.21"},
            {"name": "namespace/image", "tag": "3.21-alpha"}
        ]
        invalid_image_formats = [
            {"name": "not_valid/"},
            {"name": "/not-valid", "tag": ""},
            {"name": "/not-valid"},
            {"name": "image", "tag": ""},
            {"name": "namespace//image"},
            {"name": "not_valid/"}
        ]
        mocker.patch(
            'app.models.task.Keycloak',
            return_value=Mock()
        )
        for im_format in valid_image_formats:
            container_body.update(im_format)
            Container.validate(container_body)

        for im_format in invalid_image_formats:
            container_body["name"] = im_format
            with pytest.raises(InvalidRequest):
                Container.validate(container_body)
