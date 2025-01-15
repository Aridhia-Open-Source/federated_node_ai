from base64 import b64encode
import requests
import logging

from app.helpers.kubernetes import KubernetesClient


logger = logging.getLogger('registries_handler')
logger.setLevel(logging.INFO)


class BaseRegistry:
    token_field = None
    login_url = None
    repo_login_url = None
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

    def login(self, image=None) -> str:
        """
        Check that credentials are valid (if image is None)
            else, exchanges credentials for a token with the image or repo scope
        """
        response_auth = requests.get(
            self.repo_login_url % self.get_url_string_params(image),
            **self.request_args
        )

        if not response_auth.ok:
            return None

        return response_auth.json()[self.token_field]

    def get_url_string_params(self, image:str) -> dict[str,str]:
        return {
            "service": self.registry,
            "image": image.name if image else '',
            "organization": self.organization
        }

    def find_image_repo(self, image) -> bool:
        """
        Works as an existence check. If the tag for the image
        has the requested tag in the list of available tags
        return True.
        This should work on any docker Registry v2 as it's a standard
        """
        token = self.login(image)
        tags_list = []
        if not token:
            raise

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
    login_url = "https://%(service)s/oauth2/token?service=%(service)s"
    repo_login_url = "https://%(service)s/oauth2/token?service=%(service)s&scope=repository:%(image)s:metadata_read"
    tags_url = "https://%(service)s/v2/%(image)s/tags/list"
    token_field = "access_token"
    needs_auth = True

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.auth = b64encode(f"{self.creds['user']}:{self.creds['token']}".encode()).decode()
        self.request_args["headers"] = {"Authorization": f"Basic {self.auth}"}

    def find_image_repo(self, image) -> bool:
        tags_list = super().find_image_repo(image)
        if not tags_list:
            return False

        if tags_list.get("tags"):
            return image.tag in [t for t in tags_list.get("tags", [])]


class DockerRegistry(BaseRegistry):
    login_url = "https://hub.docker.com/v2/users/login/"
    tags_url = "https://hub.docker.com/v2/repositories/%(image)s/tags"
    token_field = "token"
    needs_auth = True

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.request_args["json"] = {"username": self.creds['user'], "password": self.creds['token']}
        self.request_args["headers"] = {"Content-Type": "application/json"}

    def find_image_repo(self, image:str) -> bool:
        tags_list = super().find_image_repo(image)

        return image.tag in [t["name"] for t in tags_list["results"]]


class GitHubRegistry(BaseRegistry):
    login_url = None
    tags_url = "https://api.github.com/orgs/%(organization)s/packages/container/%(image)s/versions"
    needs_auth = False

    def __init__(self, registry:str, secret_name:str=None, creds:dict={}):
        super().__init__(registry, secret_name, creds)

        self.auth = self.creds['token']
        self.request_args["headers"] = {}
        self.organization = registry.split('/')[1]

    def login(self, image) -> str:
        logging.info("Auth on github skipped, an organization name is needed")
        return self.auth

    def find_image_repo(self, image) -> bool:
        tags_list = super().find_image_repo(image)

        return image.tag in [t for tags in tags_list for t in tags["metadata"]["container"]["tags"]]
