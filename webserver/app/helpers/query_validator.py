import logging
import sqlalchemy
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.helpers.const import build_sql_uri
from app.models.datasets import Datasets


def connect_to_dataset(dataset:Datasets) -> sessionmaker:
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


def validate(query:str, dataset:Datasets) -> bool:
    """
    Simple method to validate SQL syntax, and against
    the actual dataset.
    """
    try:
        with connect_to_dataset(dataset)() as session:
            session.execute(text(query)).all()
        return True
    except sqlalchemy.exc.ProgrammingError as e:
        logging.info(f"Query validation failed\n{str(e)}")
        return False
