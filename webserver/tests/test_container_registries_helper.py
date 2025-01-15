import responses


def test_cr_login_failed(
        container,
        cr_class,
        cr_name
):
    """
    Test that the Container registry helper behaves as expected when the login fails.
    """
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"https://{cr_name}/oauth2/token?service={cr_name}&scope=repository:{container.name}:metadata_read",
            status=401
        )
        assert not cr_class.login(container)

def test_cr_metadata_empty(
        container,
        cr_class,
        cr_name
):
    """
    Test that the Container registry helper behaves as expected when the
        metadata response is empty. Which is a `False`
    """
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"https://{cr_name}/oauth2/token?service={cr_name}&scope=repository:{container.name}:metadata_read",
            json={"access_token": "12345asdf"},
            status=200
        )
        rsps.add(
            responses.GET,
            f"https://{cr_name}/v2/{container.name}/tags/list",
            json=[],
            status=200
        )
        assert not cr_class.find_image_repo(container)

def test_cr_metadata_tag_not_in_api_response(
        container,
        cr_class,
        cr_name
):
    """
    Test that the Container registry helper behaves as expected when the
        tag is not in the list of the metadata info. Which is a `False`
    """
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"https://{cr_name}/oauth2/token?service={cr_name}&scope=repository:{container.name}:metadata_read",
            json={"access_token": "12345asdf"},
            status=200
        )
        rsps.add(
            responses.GET,
            f"https://{cr_name}/v2/{container.name}/tags/list",
            json={"tags": ["1.2.3", "dev"]},
            status=200
        )
        assert not cr_class.find_image_repo(container)
