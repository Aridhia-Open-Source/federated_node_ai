from flask import Flask
import logging
from app import admin_api, datasets_api, tasks_api
from app.helpers.db import build_sql_uri, db
from app.helpers.exceptions import (
    InvalidDBEntry, DBError, DBRecordNotFoundError, InvalidRequest,
    AuthenticationError, KeycloakError, TaskImageException, exception_handler
)
logging.basicConfig(level=logging.WARN)

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = build_sql_uri()
    db.init_app(app)
    from app import main, requests_api
    app.register_blueprint(main.bp)
    app.register_blueprint(datasets_api.bp)
    app.register_blueprint(requests_api.bp)
    app.register_blueprint(tasks_api.bp)
    app.register_blueprint(admin_api.bp)

    app.register_error_handler(InvalidDBEntry, exception_handler)
    app.register_error_handler(DBError, exception_handler)
    app.register_error_handler(DBRecordNotFoundError, exception_handler)
    app.register_error_handler(InvalidRequest, exception_handler)
    app.register_error_handler(AuthenticationError, exception_handler)
    app.register_error_handler(KeycloakError, exception_handler)
    app.register_error_handler(TaskImageException, exception_handler)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app
