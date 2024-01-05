import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base


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

Base.query = db_session.query_property()
metadata_obj = MetaData()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import app.models.datasets
    Base.metadata.create_all(bind=engine)
