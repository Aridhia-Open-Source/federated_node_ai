import docker
import logging
import os
import re
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, db
from app.models.datasets import Datasets
from app.helpers.exceptions import InvalidRequest, TaskImageException

logger = logging.getLogger('task_model')
logger.setLevel(logging.INFO)

class Tasks(db.Model, BaseModel):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    docker_image = Column(String(256), nullable=False)
    description = Column(String(2048))
    status = Column(String(64), default='scheduled')
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    # This will be a FK or a Keycloak UUID. Something to track a user
    requested_by = Column(String(64), nullable=False)
    dataset_id = Column(Integer, ForeignKey(Datasets.id, ondelete='CASCADE'))
    dataset = relationship("Datasets")

    def __init__(self,
                 title:str,
                 docker_image:str,
                 requested_by:str,
                 dataset:Datasets,
                 description:str = '',
                 created_at:datetime=datetime.now()
                 ):
        self.title = title
        self.status = 'scheduled'
        self.docker_image = docker_image
        self.requested_by = requested_by
        self.dataset = dataset
        self.description = description
        self.created_at = created_at
        self.updated_at = datetime.now()

    def can_image_be_found(self):
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
