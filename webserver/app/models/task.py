<<<<<<< HEAD
import logging
import json
import os
import re
from datetime import datetime
from kubernetes.client.exceptions import ApiException
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

import urllib3
from app.helpers.acr import ACRClient
from app.helpers.db import BaseModel, db
from app.helpers.keycloak import Keycloak
from app.helpers.kubernetes import TASK_NAMESPACE, KubernetesBatchClient, KubernetesClient
from app.helpers.query_validator import validate as validate_query
from app.helpers.exceptions import DBError, InvalidRequest, TaskImageException, TaskExecutionException
from app.models.dataset import Dataset
=======
import docker
import logging
import os
import re
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, db
from app.models.dataset import Dataset
from app.helpers.exceptions import InvalidRequest, TaskImageException
>>>>>>> main

logger = logging.getLogger('task_model')
logger.setLevel(logging.INFO)

<<<<<<< HEAD
TASK_POD_RESULTS_PATH = os.getenv("TASK_POD_RESULTS_PATH")
RESULTS_PATH = os.getenv("RESULTS_PATH")

class Task(db.Model, BaseModel):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
=======
class Task(db.Model, BaseModel):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
>>>>>>> main
    docker_image = Column(String(256), nullable=False)
    description = Column(String(2048))
    status = Column(String(64), default='scheduled')
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    # This will be a FK or a Keycloak UUID. Something to track a user
    requested_by = Column(String(64), nullable=False)
    dataset_id = Column(Integer, ForeignKey(Dataset.id, ondelete='CASCADE'))
    dataset = relationship("Dataset")

    def __init__(self,
<<<<<<< HEAD
                 name:str,
                 docker_image:str,
                 requested_by:str,
                 dataset:Dataset,
                #  command:str = '',
                #  environment:dict = {},
                 executors:dict = {},
                 tags:dict = {},
                 resources:dict = {},
                 inputs:dict = {},
                 outputs:dict = {},
                 volumes:dict = {},
                 description:str = '',
                 created_at:datetime=datetime.now()
                 ):
        self.name = name
=======
                 title:str,
                 docker_image:str,
                 requested_by:str,
                 dataset:Dataset,
                 description:str = '',
                 created_at:datetime=datetime.now()
                 ):
        self.title = title
>>>>>>> main
        self.status = 'scheduled'
        self.docker_image = docker_image
        self.requested_by = requested_by
        self.dataset = dataset
        self.description = description
        self.created_at = created_at
        self.updated_at = datetime.now()
<<<<<<< HEAD
        # self.command = self._parse_command(command)
        self.tags = tags
        # self.environment = environment
        self.executors = executors
        self.resources = resources
        self.inputs = inputs
        self.outputs = outputs
        self.volumes = volumes

    @classmethod
    def validate(cls, data:dict):
        data["requested_by"] = Keycloak().decode_token(
            Keycloak.get_token_from_headers()
        ).get('sub')
        # Support only for one image at a time, the standard is executors == list
        executors = data["executors"][0]
        data["docker_image"] = executors["image"]
        # data["command"] = executors["command"]
        # data["environment"] = executors["env"]
        data = super().validate(data)

        # query = data.pop('use_query')
        ds_id = data.get("tags", {}).get("dataset_id")
        data["dataset"] = db.session.get(Dataset, ds_id)

        # if not validate_query(query, data["dataset"]):
        #     raise InvalidRequest("Query missing or misformed")

        if not re.match(r'^((\w+|-)\/?\w+)+:(\w+(\.|-)?)+$', data["docker_image"]):
            raise InvalidRequest(
                f"{data["docker_image"]} does not have a tag. Please provide one in the format <image>:<tag>"
            )
        cls.can_image_be_found(data["docker_image"])
        return data

    def _parse_command(self, command:str) -> list[str]:
        """
        A docker command has to follow a certain structure.
        Anything within double quotes should be enclosed in a single
        list element.
        Rest should be split for whitespaces and live in a separate list item
        i.e.:
            command -> sh -c "./script.sh arg1"
            returns -> ["sh", "-c", "./script.sh arg1"]
        """
        if command:
            no_quotes_cmd = [cmd for cmd in command.split("\"") if cmd]
            return no_quotes_cmd[0].split(" ")[:-1] + no_quotes_cmd[1:]
        return None

    @classmethod
    def can_image_be_found(cls, docker_image):
=======

    def can_image_be_found(self):
>>>>>>> main
        """
        Looks through the ACR if the image exists
        """
        acr_url = os.getenv('ACR_URL')
        acr_username = os.getenv('ACR_USERNAME')
        acr_password = os.getenv('ACR_PASSWORD')
        auth_config = {
            "username": acr_username,
            "password": acr_password
        }
<<<<<<< HEAD
        acr_client = ACRClient(url=acr_url, **auth_config)
        if not acr_client.has_image_metadata(docker_image):
            raise TaskImageException(f"Image {docker_image} not found on our repository")

    def pod_name(self):
        return f"{self.name.lower().replace(' ', '-')}-{self.requested_by}"

    def run(self, validate=False):
        """
        Method to spawn a new pod with the requested image
        : param validate : An optional parameter to basically run in dry_run mode
            Defaults to False
        """
        v1 = KubernetesClient()
        body = v1.create_pod_spec({
            "name": self.pod_name(),
            "image": self.docker_image,
            "labels": {
                "task_id": str(self.id),
                "requested_by": self.requested_by
            },
            "dry_run": 'true' if validate else 'false',
            "environment": self.executors[0]["env"],
            "command": self.executors[0]["command"],
            "mount_path": TASK_POD_RESULTS_PATH
        })
        try:
            current_pod = self.get_current_pod()
            if current_pod:
                raise TaskExecutionException("Pod is already running", code=409)

            v1.create_namespaced_pod(
                namespace=TASK_NAMESPACE,
                body=body,
                pretty='true'
            )
        except ApiException as e:
            logger.error(json.loads(e.body))
            raise InvalidRequest(f"Failed to run pod: {e.reason}")

    def get_current_pod(self):
        v1 = KubernetesClient()
        running_pods = v1.list_namespaced_pod('tasks')
        try:
            return [pod for pod in running_pods.items if pod.metadata.name == self.pod_name()][0]
        except IndexError:
            return

    def get_status(self) -> dict | str:
        """
        k8s sdk returns a bunch of nested objects as a pod's status.
        Here the objects are deconstructed and a customized dictionary is returned
            according to the possible states.
        Returns:
            :dict: if the pod exists
            :str: if the pod is not found or deleted
        """
        try:
            status_obj = self.get_current_pod().status.container_statuses[0].state
            for status in ['running', 'waiting', 'terminated']:
                st = getattr(status_obj, status)
                if st is not None:
                    break

            self.status = status
            returned_status =  {
                "started_at": st.started_at
            }
            if status == 'terminated':
                returned_status.update({
                    "finished_at": getattr(st, "finished_at", None),
                    "exit_code": getattr(st, "exit_code", None),
                    "reason": getattr(st, "reason", None)
                })
            return {
                status: returned_status
            }
        except AttributeError:
            return self.status if self.status != 'running' else 'deleted'

    def terminate_pod(self):
        v1 = KubernetesClient()
        has_error = False
        try:
            v1.delete_namespaced_pod(self.pod_name(), namespace=TASK_NAMESPACE)
        except ApiException as kexc:
            logger.error(kexc.reason)
            has_error = True

        try:
            self.status = 'cancelled'
        except Exception as exc:
            raise DBError("An error occurred while updating") from exc

        if has_error:
            raise TaskExecutionException("Task already cancelled")
        return self.sanitized_dict()

    def get_results(self):
        """
        The idea is to create a job that holds indefinitely
        so that the backend can copy the results
        """
        v1_batch = KubernetesBatchClient()
        job_name = f"result-job-{uuid4()}"
        job = v1_batch.create_job_spec({
            "name": job_name,
            "persistent_volumes": [
                {
                    "name": f"{self.pod_name()}-volclaim",
                    "mount_path": TASK_POD_RESULTS_PATH,
                    "vol_name": "data"
                }
            ],
            "labels": {
                "task_id": str(self.id),
                "requested_by": self.requested_by
            }
        })
        try:
            v1_batch.create_namespaced_job(
                namespace=TASK_NAMESPACE,
                body=job,
                pretty='true'
            )
            # Get the job's pod
            v1 = KubernetesClient()
            job_pod = list(filter(lambda x: x.metadata.labels.get('job-name') == job_name, v1.list_namespaced_pod(namespace=TASK_NAMESPACE).items))[0]

            # TODO Need to find a more dynamic way for this to work. Pod is not ready immediately
            import time
            time.sleep(1)
            res_file = v1.cp_from_pod(job_pod.metadata.name, TASK_POD_RESULTS_PATH, f"{RESULTS_PATH}/{self.id}")

            v1.delete_pod(job_name)
            v1.delete_pod(job_pod.metadata.name)
        except ApiException as e:
            logger.error(getattr(e, 'reason'))
            raise InvalidRequest(f"Failed to run pod: {e.reason}")
        except urllib3.exceptions.MaxRetryError:
            raise InvalidRequest("The cluster could not create the job")
        return res_file
=======
        try:
            client = docker.from_env()
            client.login(registry=acr_url, **auth_config)

            client.images.get_registry_data(
                f"{acr_url}/{self.docker_image}",
                auth_config=auth_config
            )
        except docker.errors.NotFound:
            raise TaskImageException(f"Image {self.docker_image} not found on our repository")
        except docker.errors.APIError as dexc:
            logger.info(dexc.explanation)
            raise TaskImageException("Problem connecting to the Image Registry")

    @classmethod
    def validate(cls, data:dict):
        valid = super().validate(data)
        if not re.match(r'(\d|\w|\_|\-|\/)+:(\d|\w|\_|\-)+', valid["docker_image"]):
            raise InvalidRequest(
                f"{valid["docker_image"]} does not have a tag. Please provide one in the format <image>:<tag>"
            )
        return valid
>>>>>>> main
