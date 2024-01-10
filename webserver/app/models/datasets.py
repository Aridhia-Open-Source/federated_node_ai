from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, Base


class Datasets(Base, BaseModel):
    __tablename__ = 'datasets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    host = Column(String(120), nullable=False)
    # catalogue_id = Column(Integer, ForeignKey("catalogues.id", ondelete="CASCADE"))
    # dictionary_id = Column(Integer, ForeignKey("dictionaries.id", ondelete="CASCADE"))

    def __init__(self, name:str=None, host:str=None):
        self.name = name
        self.host = host

    def __repr__(self):
        return f'<Dataset {self.name!r}>'


class Catalogues(Base, BaseModel):
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
                 created_at:datetime=datetime.now(),
                 updated_at:datetime=datetime.now()
        ):
        self.version = version
        self.title = title
        self.dataset = dataset
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at


class Dictionaries(Base, BaseModel):
    __tablename__ = 'dictionaries'
    __table_args__ = (
        UniqueConstraint('table_name', 'dataset_id', 'field_name'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    field_name = Column(String(50))
    label = Column(String(64))
    description = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    dataset_id = Column(Integer, ForeignKey(Datasets.id, ondelete='CASCADE'))
    dataset = relationship("Datasets")

    def __init__(self,
                 table_name:str,
                 description:str,
                 dataset:Datasets,
                 label:str='',
                 field_name:str='',
                 created_at:datetime=datetime.now(),
                 updated_at:datetime=datetime.now()
                 ):
        self.table_name = table_name
        self.description = description
        self.dataset = dataset
        self.label = label
        self.field_name = field_name
        self.created_at = created_at
        self.updated_at = updated_at
