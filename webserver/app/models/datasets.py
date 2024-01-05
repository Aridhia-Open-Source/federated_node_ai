from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from app.helpers.db import BaseModel, Base
from app.exceptions import InvalidDBEntry


class Datasets(Base, BaseModel):
    __tablename__ = 'datasets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True)
    host = Column(String(120))
    catalogue_id = Column(Integer, ForeignKey("catalogues.id", ondelete="CASCADE"))
    dictionary_id = Column(Integer, ForeignKey("dictionaries.id", ondelete="CASCADE"))

    def __init__(self, name:str=None, host:str=None):
        self.name = name
        self.host = host

    def __repr__(self):
        return f'<Dataset {self.name!r}>'

    @staticmethod
    def validate(data:dict):
        """
        Make sure we have all required fields. Set to None if missing
        """
        required_fields = ["name", "url"]
        valid = data.copy()
        for k, v in data.items():
            if k not in required_fields:
                 valid[k] = None
            elif v is None:
                raise InvalidDBEntry(f"Field {k} has invalid value")
        for req_field in required_fields:
            if req_field not in list(valid.keys()):
                raise InvalidDBEntry(f"Field \"{req_field}\" missing")
        return valid


class Catalogues(Base, BaseModel):
    __tablename__ = 'catalogues'
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(10))
    title = Column(String(256), nullable=False)
    description = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())


class Dictionaries(Base, BaseModel):
    __tablename__ = 'dictionaries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50))
    field_name = Column(String(50))
    label = Column(String(64))
    description = Column(String(2048))
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
