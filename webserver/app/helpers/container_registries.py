from base64 import b64encode
import requests
import logging
from requests.exceptions import ConnectionError

from app.helpers.kubernetes import KubernetesClient
from app.helpers.exceptions import ContainerRegistryException


logger = logging.getLogger('registries_handler')
logger.setLevel(logging.INFO)


class BaseRegistry:
    token_field = None
    login_url = None
    repo_login_url = None
    list_repo_url = None
    creds = None
    organization = ''
    request_args = {}

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        self.registry = registry
        self.secret_name = secret_name
        self.creds = creds
        if secret_name is not None:
            self.creds = self.get_secret()

    def get_secret(self) -> dict[str,str]:
        """
        Get the registry-related secret
        """
        v1 = KubernetesClient()
        secret = v1.read_namespaced_secret(self.secret_name, 'default', pretty='pretty')
        return {
            "user": KubernetesClient.decode_secret_value(secret.data['USER']),
            "token": KubernetesClient.decode_secret_value(secret.data['TOKEN'])
        }

    def list_repos(self) -> list[str]:
        """
        Depending on the provider, will need to run
            different api requests to get a list of
            available images
        """
        token = self.login()
        if not token:
            raise ContainerRegistryException("Could not login to the Registry")
        list_resp = requests.get(
            self.list_repo_url % {"service": self.registry, "organization": self.organization},
            headers={"Authorization": f"Bearer {token}"}
        )
        if not list_resp.ok:
            logger.error(list_resp.text)
            raise ContainerRegistryException("Could not fetch the list of images", 500)

        return list_resp.json()

    def login(self, image=None) -> str:
        """
        Check that credentials are valid (if image is None)
            else, exchanges credentials for a token with the image or repo scope
        """
        url = self.repo_login_url if image else  self.login_url
        try:
            response_auth = requests.get(
                url % self.get_url_string_params(image),
                **self.request_args
            )

            if not response_auth.ok:
                return None

            return response_auth.json()[self.token_field]
        except ConnectionError as ce:
            logger.error(ce)
            raise ContainerRegistryException(
                "Failed to connect with the Registry. Make sure it's spelled correctly"
                " or it does not have firewall restrictions.",
                500
            )

    def get_url_string_params(self, image:str) -> dict[str,str]:
        return {
            "service": self.registry,
            "image": image if image else '',
            "organization": self.organization
        }

    def get_image_tags(self, image) -> bool:
        """
        Works as an existence check. If the tag for the image
        has the requested tag in the list of available tags
        return True.
        This should work on any docker Registry v2 as it's a standard
        """
        token = self.login(image)
        if not token:
            raise ContainerRegistryException("Could not login to the Registry")

        tags_list = []
        try:
            response_metadata = requests.get(
                self.tags_url % self.get_url_string_params(image),
                headers={"Authorization": f"Bearer {token}"}
            )
            if response_metadata.ok:
                tags_list = response_metadata.json()
            else:
                logger.info(response_metadata.text)
        except ConnectionError as ce:
            logger.info(ce.strerror)

        return tags_list


class AzureRegistry(BaseRegistry):
    login_url = "https://%(service)s/oauth2/token?service=%(service)s&scope=registry:catalog:*"
    repo_login_url = "https://%(service)s/oauth2/token?service=%(service)s&scope=repository:%(image)s:metadata_read"
    tags_url = "https://%(service)s/v2/%(image)s/tags/list"
    list_repo_url = "https://%(service)s/v2/_catalog"
    token_field = "access_token"

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.auth = b64encode(f"{self.creds['user']}:{self.creds['token']}".encode()).decode()
        self.request_args["headers"] = {"Authorization": f"Basic {self.auth}"}

    def get_image_tags(self, image, tag=None) -> bool:
        tags_list = super().get_image_tags(image)
        if not tags_list:
            return False

        if not tag:
            return [t for t in tags_list.get("tags", [])]
        return tag in [t for t in tags_list.get("tags", [])]

    def list_repos(self):
        list_images = super().list_repos()
        images = []
        for image in list_images["repositories"]:
            images.append({"name": image, "tags": self.get_image_tags(image)})
        return images

class DockerRegistry(BaseRegistry):
    repo_login_url = "https://hub.docker.com/v2/users/login/"
    login_url = "https://hub.docker.com/v2/users/login/"
    tags_url = "https://hub.docker.com/v2/repositories/%(image)s/tags"
    list_repo_url = "https://hub.docker.com/v2/repositories/%(organization)s"
    token_field = "token"

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.request_args["json"] = {"username": self.creds['user'], "password": self.creds['token']}
        self.request_args["headers"] = {"Content-Type": "application/json"}

    def get_image_tags(self, image:str, tag:str=None) -> bool:
        tags_list = super().get_image_tags(image)

        if not tag:
            return [t["name"] for t in tags_list["results"]]
        return tag in [t["name"] for t in tags_list["results"]]


class GitHubRegistry(BaseRegistry):
    login_url = None
    tags_url = "https://api.github.com/orgs/%(organization)s/packages/container/%(image)s/versions"
    list_repo_url = "https://api.github.com/orgs/%(organization)s/packages?package_type=container"

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.auth = self.creds['token']
        self.request_args["headers"] = {}
        self.organization = registry.split('/')[1]

    def login(self, image=None) -> str:
        logging.info("Auth on github skipped, an organization name is needed")
        return self.auth

    def get_image_tags(self, image:str, tag:str=None) -> bool:
        tags_list = super().get_image_tags(image)
        if not tag:
            return [t for tags in tags_list for t in tags["metadata"]["container"]["tags"]]

        return tag in [t for tags in tags_list for t in tags["metadata"]["container"]["tags"]]

    def list_repos(self):
        list_images = super().list_repos()
        images = []
        for img in list_images:
            images.append({
                "name": img["name"],
                "tags": self.get_image_tags(img["name"])
            })
        return images
