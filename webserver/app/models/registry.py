import re
from sqlalchemy import Column, Integer, String, Boolean

from app.helpers.const import DEFAULT_NAMESPACE
from app.helpers.container_registries import AzureRegistry, BaseRegistry, DockerRegistry, GitHubRegistry
from app.helpers.db import BaseModel, db
from app.helpers.kubernetes import KubernetesClient
from app.helpers.exceptions import ContainerRegistryException


class Registry(db.Model, BaseModel):
    __tablename__ = 'registries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(256), nullable=False)
    needs_auth = Column(Boolean, default=True)

    def __init__(
            self,
            url: str,
            username: str,
            password: str,
            needs_auth:bool=True
        ):
        self.url = url
        self.needs_auth = needs_auth
        self.username = username
        self.password = password

    @classmethod
    def validate(cls, data:dict):
        data = super().validate(data)

        # Test credentials
        _class = cls(**data).get_registry_class()
        if isinstance(_class, GitHubRegistry):
            destruct_reg = _class.registry.split('/')
            if len(destruct_reg) <= 1:
                raise ContainerRegistryException("For GitHub registry, provide the org name. i.e. ghcr.io/orgname")

        _class.login()
        return data

    def _get_name(self):
        return re.sub('^http(s{,1})://', '', self.url)

    def add(self, commit=True):
        v1 = KubernetesClient()
        v1.create_secret(
            name=self.slugify_name(),
            values={
                "USER": self.username,
                "TOKEN": self.password
            },
            namespaces=[DEFAULT_NAMESPACE]
        )
        super().add(commit)

    def _get_creds(self):
        if hasattr(self, "username") and hasattr(self, "password"):
            return {"user": self.username, "token": self.password}

    def slugify_name(self) -> str:
        """
        Based on the provided name, it will return the slugified name
        so that it will be sade to save on the DB
        """
        return re.sub(r'[\W_]+', '-', self._get_name())

    def get_registry_class(self) -> BaseRegistry:
        """
        We have interface classes with dedicated login, and
        image tag parsers. Based on the registry name
        infers the appropriate class
        """
        args = {
            "registry": self._get_name(),
            "creds": self._get_creds()
        }
        if self.id:
            args["secret_name"]= self.slugify_name()
        matches = re.search(r'azurecr\.io|ghcr\.io', self.url)

        matches = '' if matches is None else matches.group()

        match matches:
            case 'azurecr.io':
                return AzureRegistry(**args)
            case 'ghcr.io':
                return GitHubRegistry(**args)
            case _:
                return DockerRegistry(**args)

    def fetch_image_list(self) -> list[str]:
        """
        Simply returns a list of strings of all available
            images (or repos) with their tags
        """
        _class = self.get_registry_class()
        return _class.list_repos()
