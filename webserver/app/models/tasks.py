import os
import docker
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, db
from .datasets import Datasets


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
        # client = docker.from_env()
        # client.list()
        return True

