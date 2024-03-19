import logging
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError, InternalError

from app.helpers.const import build_sql_uri
from app.models.dataset import Dataset

logger = logging.getLogger('query_validator')
logger.setLevel(logging.INFO)

def connect_to_dataset(dataset:Dataset) -> sessionmaker:
    """
    Given a datasets object, create a connection string
    and return a session that can be used to send queries
    """
    user, passw = dataset.get_credentials()
    engine = create_engine(build_sql_uri(
        host=re.sub('http(s)*://', '', dataset.host),
        port=dataset.port,
        username=user,
        password=passw,
        database=dataset.name
    ))
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

def validate(query:str, dataset:Dataset) -> bool:
    """
    Simple method to validate SQL syntax, and against
    the actual dataset.
    """
    try:
        with connect_to_dataset(dataset)() as session:
            # Read only query, so things like UPDATE, DELETE or DROP won't be executed
            session.execute(text('SET TRANSACTION READ ONLY'))
            session.execute(text(query)).all()
        return True
    except (ProgrammingError, OperationalError, InternalError) as exc:
        logger.info(f"Query validation failed\n{str(exc)}")
        return False
