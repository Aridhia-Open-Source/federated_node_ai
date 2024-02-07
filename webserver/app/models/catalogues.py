from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, db
from app.models.datasets import Datasets

class Catalogues( db.Model, BaseModel):
    __tablename__ = 'catalogues'
    __table_args__ = (
        UniqueConstraint('title', 'dataset_id'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(10))
    title = Column(String(256), nullable=False)
    description = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    dataset_id = Column(Integer, ForeignKey(Datasets.id, ondelete='CASCADE'))
    dataset = relationship("Datasets")

    def __init__(self,
                 title:str,
                 description:str,
                 dataset:Datasets,
                 version:str='1',
                 created_at:datetime=datetime.now()
        ):
        self.version = version
        self.title = title
        self.dataset = dataset
        self.description = description
        self.created_at = created_at
        self.updated_at = datetime.now()
