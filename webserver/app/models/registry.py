import base64
import json
import logging
import re
from kubernetes.client.exceptions import ApiException
from sqlalchemy import Column, Integer, String, Boolean

from app.helpers.const import DEFAULT_NAMESPACE, TASK_NAMESPACE, TASK_PULL_SECRET_NAME
from app.helpers.container_registries import AzureRegistry, BaseRegistry, DockerRegistry, GitHubRegistry
from app.helpers.base_model import BaseModel, db
from app.helpers.exceptions import ContainerRegistryException, InvalidRequest
from app.helpers.kubernetes import KubernetesClient

logger = logging.getLogger("registry_model")
logger.setLevel(logging.INFO)


class Registry(db.Model, BaseModel):
    __tablename__ = 'registries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(256), nullable=False)
    needs_auth = Column(Boolean, default=True)
    active = Column(Boolean, default=True)

    def __init__(
            self,
            url: str,
            username: str,
            password: str,
            needs_auth:bool=True,
            active:bool=True
        ):
        self.url = url
        self.needs_auth = needs_auth
        self.active = active
        self.username = username
        self.password = password

    def sanitized_dict(self):
        san_dict = super().sanitized_dict()
        keys = list(san_dict.keys())
        for k in keys:
            if k not in self._get_fields_name():
                san_dict.pop(k, None)
        return san_dict

    @classmethod
    def validate(cls, data:dict):
        data = super().validate(data)

        # Test credentials
        _class = cls(**data).get_registry_class()
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
        self.update_regcred()
        super().add(commit)

    def update_regcred(self):
        """
        Every time a new registry is added, we should propagate
        the changes to the regcred secret in the task namespace
        so we can pull those images
        """
        v1 = KubernetesClient()
        try:
            regcred = v1.read_namespaced_secret(TASK_PULL_SECRET_NAME, TASK_NAMESPACE)
        except ApiException as kae:
            if kae.status == 404:
                regcred = v1.create_secret(
                    name=TASK_PULL_SECRET_NAME,
                    values={
                        ".dockerconfigjson": json.dumps({"auths" : {}})
                    },
                    namespaces=[TASK_NAMESPACE],
                    type='kubernetes.io/dockerconfigjson'
                )
            else:
                raise ContainerRegistryException(
                    "Something went wrong while updating secrets"
                ) from kae

        dockerjson = json.loads(v1.decode_secret_value(regcred.data['.dockerconfigjson']))
        dockerjson['auths'].update({
            self.url: {
                "username": self.username,
                "password": self.password,
                "email": "",
                "auth": base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            }
        })
        regcred.data['.dockerconfigjson'] = v1.encode_secret_value(json.dumps(dockerjson))
        v1.patch_namespaced_secret(namespace=TASK_NAMESPACE, name=TASK_PULL_SECRET_NAME, body=regcred)

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

    def delete(self, commit:bool=False):
        session = db.session
        super().delete(commit)
        v1 = KubernetesClient()
        try:
            regcred = v1.read_namespaced_secret(TASK_PULL_SECRET_NAME, TASK_NAMESPACE)
            dockerjson = json.loads(v1.decode_secret_value(regcred.data['.dockerconfigjson']))
            dockerjson['auths'].pop(self.url, None)
            regcred.data['.dockerconfigjson'] = v1.encode_secret_value(json.dumps(dockerjson))
            v1.patch_namespaced_secret(namespace=TASK_NAMESPACE, name=TASK_PULL_SECRET_NAME, body=regcred)

            v1.delete_namespaced_secret(name=self.slugify_name(), namespace=DEFAULT_NAMESPACE)
        except ApiException as kae:
            session.rollback()
            logger.error("%s:\n\tDetails: %s", kae.reason, kae.body)
            raise ContainerRegistryException("Error while deleting entity")

    def update(self, **kwargs) -> None:
        """
        Updates the instance with new values. These should be
        already validated.
        """
        for key in kwargs.keys():
            if key not in ["username", "password", "active"]:
                raise InvalidRequest(f"Field {key} is not valid")

        if kwargs.get("active") is not None:
            self.query.filter(Registry.id == self.id).update(
                {"active": kwargs.get("active")},
                synchronize_session='evaluate'
            )

        if not(kwargs.get("username") or kwargs.get("password")):
            return

        # Get the credentials from the pull docker secret
        v1 = KubernetesClient()
        try:
            secret = v1.read_namespaced_secret(self.slugify_name(), namespace=DEFAULT_NAMESPACE)
            regcred = v1.read_namespaced_secret(TASK_PULL_SECRET_NAME, TASK_NAMESPACE)
            dockerjson = json.loads(v1.decode_secret_value(regcred.data['.dockerconfigjson']))
            self.username = dockerjson['auths'][self.url]["username"]
            self.password = dockerjson['auths'][self.url]["password"]

            if kwargs.get("username"):
                self.username = kwargs.get("username")
                secret.data["USER"] = KubernetesClient.encode_secret_value(self.username)

            if kwargs.get("password"):
                self.password = kwargs.get("password")
                secret.data["TOKEN"] = KubernetesClient.encode_secret_value(self.password)

            self.update_regcred()
            v1.patch_namespaced_secret(namespace=DEFAULT_NAMESPACE, name=self.slugify_name(), body=secret)
        except ApiException as apie:
            logger.error("Reason: %s\nDetails: %s", apie.reason, apie.body)
            raise InvalidRequest("Could not update credentials") from apie
