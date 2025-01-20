import responses


class TestAzureRegistry:
    """
    Different registry classes make different requests.
        This addressed the Azure case
    """
    def test_cr_login_failed(
            self,
            container_az,
            az_cr_class,
            azure_cr_name,
            registry_az
    ):
        """
        Test that the Container registry helper behaves as expected when the login fails.
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://{azure_cr_name}/oauth2/token?service={registry_az.url}&scope=repository:{container_az.name}:metadata_read",
                status=401
            )
            assert not az_cr_class.login(container_az.name)

    def test_cr_metadata_empty(
            self,
            container_az,
            az_cr_class,
            azure_cr_name
    ):
        """
        Test that the Container registry helper behaves as expected when the
            metadata response is empty. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://{azure_cr_name}/oauth2/token?service={azure_cr_name}&scope=repository:{container_az.name}:metadata_read",
                json={"access_token": "12345asdf"},
                status=200
            )
            rsps.add(
                responses.GET,
                f"https://{azure_cr_name}/v2/{container_az.name}/tags/list",
                json=[],
                status=200
            )
            assert not az_cr_class.get_image_tags(container_az.name)

    def test_cr_metadata_tag_not_in_api_response(
            self,
            container_az,
            az_cr_class,
            azure_cr_name
    ):
        """
        Test that the Container registry helper behaves as expected when the
            tag is not in the list of the metadata info. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://{azure_cr_name}/oauth2/token?service={azure_cr_name}&scope=repository:{container_az.name}:metadata_read",
                json={"access_token": "12345asdf"},
                status=200
            )
            rsps.add(
                responses.GET,
                f"https://{azure_cr_name}/v2/{container_az.name}/tags/list",
                json={"tags": ["1.2.3", "dev"]},
                status=200
            )
            assert not az_cr_class.get_image_tags(container_az.name, "latest")


class TestGitHubRegistry:
    """
    Different registry classes make different requests.
        This addressed the github case, where login is not
        strictly a separate action
    """
    def test_cr_metadata_empty(
            self,
            container_gh,
            gh_cr_class
    ):
        """
        Test that the Container registry helper behaves as expected when the
            metadata response is empty. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://api.github.com/orgs/{gh_cr_class.organization}/packages/container/{container_gh.name}/versions",
                json=[],
                status=200
            )
            assert not gh_cr_class.get_image_tags(container_gh.name)

    def test_cr_metadata_tag_not_in_api_response(
            self,
            container_gh,
            gh_cr_class
    ):
        """
        Test that the Container registry helper behaves as expected when the
            tag is not in the list of the metadata info. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"https://api.github.com/orgs/{gh_cr_class.organization}/packages/container/{container_gh.name}/versions",
                json=[{
                    "metadata": {
                        "container":{
                            "tags": ["1.2.3", "dev"]
                        }
                    }
                }],
                status=200
            )
            assert not gh_cr_class.get_image_tags(container_gh.name, "latest")

class TestDockerRegistry:
    """
    Different registry classes make different requests.
        This addressed the DockerHub case
    """
    login_url = "https://hub.docker.com/v2/users/login/"
    tags_url = "https://hub.docker.com/v2/repositories/%s/tags"

    def test_cr_login_failed(
            self,
            dh_cr_class,
            container_dh
    ):
        """
        Test that the Container registry helper behaves as expected when the login fails.
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                self.login_url,
                status=401
            )
            assert not dh_cr_class.login(container_dh.name)

    def test_cr_metadata_empty(
            self,
            dh_cr_class,
            container_dh
    ):
        """
        Test that the Container registry helper behaves as expected when the
            metadata response is empty. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                self.login_url,
                json={"token": "12345asdf"},
                status=200
            )
            rsps.add(
                responses.GET,
                self.tags_url % container_dh.name,
                json={"results": []},
                status=200
            )
            assert not dh_cr_class.get_image_tags(container_dh.name)

    def test_cr_metadata_tag_not_in_api_response(
            self,
            dh_cr_class,
            container_dh
    ):
        """
        Test that the Container registry helper behaves as expected when the
            tag is not in the list of the metadata info. Which is a `False`
        """
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                self.login_url,
                json={"token": "12345asdf"},
                status=200
            )
            rsps.add(
                responses.GET,
                self.tags_url % container_dh.name,
                json={"results": [{"name": ["1.2.3", "dev"]}]},
                status=200
            )
            assert not dh_cr_class.get_image_tags(container_dh.name, "latest")

