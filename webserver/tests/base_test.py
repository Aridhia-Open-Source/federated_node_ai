import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, close_all_sessions
from app.helpers.db import Base, build_sql_uri
from app import create_app


class AbstractTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(build_sql_uri())
        # Make sure we start with a clean slate
        Base.metadata.drop_all(self.engine)

        self.db_session = Session(self.engine)
        Base.metadata.create_all(self.engine)
        app = create_app()
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        # Clear the DB
        self.db_session.rollback()
        self.db_session.commit()
        close_all_sessions()
        Base.metadata.drop_all(self.engine)
        self.ctx.pop()
