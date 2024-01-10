import os
import re
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base, Relationship

from app.exceptions import InvalidDBEntry


def build_sql_uri():
    return f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"

engine = create_engine(build_sql_uri())
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()

# Another helper class for common methods
class BaseModel():
    def sanitized_dict(self):
        jsonized = self.__dict__
        jsonized.pop('_sa_instance_state', None)
        return jsonized

    @classmethod
    def get_all(cls):
        ds = cls.query.all()
        jsonized = []
        for d in ds:
            jsonized.append(d.sanitized_dict())
        return jsonized

    @classmethod
    def _get_fields(cls):
        return [f for f in cls.__dict__.keys() if not re.match(r'^_', f)]

    @classmethod
    def is_field_required(cls, f):
        attribute = getattr(cls, f)
        return not getattr(attribute, 'nullable', True) and f != 'id' and isinstance(attribute.prop, Relationship)

    @classmethod
    def _get_required_fields(cls):
        return [f for f in cls._get_fields() if cls.is_field_required(f)]

    @classmethod
    def validate(cls, data:dict):
        """
        Make sure we have all required fields. Set to None if missing
        """
        if not data:
            raise InvalidDBEntry(f"No usable data foundfor table {cls.__tablename__}")
        valid = data.copy()
        for k, v in data.items():
            if isinstance(v, dict) or isinstance(v, list):
                continue
            if getattr(cls, k).nullable:
                 valid[k] = None
            elif v is None:
                raise InvalidDBEntry(f"Field {k} has invalid value")
        for req_field in cls._get_required_fields():
            if req_field not in list(valid.keys()):
                raise InvalidDBEntry(f"Field \"{req_field}\" missing")
        return valid

Base.query = db_session.query_property()
metadata_obj = MetaData()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import app.models.datasets
    Base.metadata.create_all(bind=engine)
