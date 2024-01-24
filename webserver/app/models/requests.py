from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, Base
from app.models.datasets import Datasets

class Requests(Base, BaseModel):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    description = Column(String(2048))

    # This will be a FK or a Keycloak UUID. Something to track a user
    requested_by = Column(String(64), nullable=False)
    project_name = Column(String(64), nullable=False)
    status = Column(String(32), default='pending')
    proj_start = Column(DateTime(timezone=False), nullable=False)
    proj_end = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    dataset_id = Column(Integer, ForeignKey(Datasets.id, ondelete='CASCADE'))
    dataset = relationship("Datasets")

    def __init__(self,
                 title:str,
                 project_name:str,
                 dataset:Datasets,
                 requested_by:str,
                 proj_start:datetime,
                 proj_end:datetime,
                 description:str='',
                 created_at:datetime=datetime.now()
        ):
        self.title = title
        self.description = description
        self.project_name = project_name
        # Not sure how to track the dataset yet, as DAR provider will have different IDs from the internal ones
        self.dataset = dataset
        self.requested_by = requested_by
        self.proj_start = proj_start
        self.proj_end = proj_end
        self.created_at = created_at
        self.updated_at = datetime.now()
