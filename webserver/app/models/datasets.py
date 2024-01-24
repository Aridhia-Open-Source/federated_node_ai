import base64
import re
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, Base
from kubernetes import client, config


class Datasets(Base, BaseModel):
    __tablename__ = 'datasets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    host = Column(String(120), nullable=False)
    port = Column(Integer, default=5432)

    def __init__(self, name:str, host:str, username:str, password:str, port:int=5432):
        self.name = name
        self.host = host
        self.port = port
        # Create secrets for credentials
        config.load_kube_config()
        v1 = client.CoreV1Api()
        body = client.V1Secret()
        body.api_version = 'v1'
        body.data = {
            "PGPASSWORD": base64.b64encode(password.encode()).decode(),
            "PGUSER": base64.b64encode(username.encode()).decode()
        }
        body.kind = 'Secret'
        body.metadata = {'name': self.get_creds_secret_name()}
        body.type = 'Opaque'
        v1.create_namespaced_secret('default', body=body, pretty='true')

    def get_creds_secret_name(self):
        return f"{re.sub('http(s)*://', '', self.host)}-{self.name.lower()}-creds"

    def get_credentials(self) -> tuple:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        secret = v1.read_namespaced_secret(self.get_creds_secret_name(), 'default', pretty='pretty')
        user = base64.b64decode(secret.data['PGUSER'].encode()).decode()
        password = base64.b64decode(secret.data['PGPASSWORD'].encode()).decode()
        return user, password

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
                 created_at:datetime=datetime.now()
        ):
        self.version = version
        self.title = title
        self.dataset = dataset
        self.description = description
        self.created_at = created_at
        self.updated_at = datetime.now()


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
                 ):
        self.table_name = table_name
        self.description = description
        self.dataset = dataset
        self.label = label
        self.field_name = field_name
        self.created_at = created_at
        self.updated_at = datetime.now()
