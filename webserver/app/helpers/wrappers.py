from functools import wraps
from flask import request
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.helpers.db import db, engine
from app.helpers.keycloak import Keycloak
from app.exceptions import AuthenticationError
from app.models.audit import Audit


def auth(scope='public'):
    def auth_wrapper(func):
        @wraps(func)
        def _auth(*args, **kwargs):
            try:
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
            except KeyError:
                raise AuthenticationError("Token not provided")

            session = db.session
            resource = 'endpoints'
            ds_id = None
            path = request.path.split('/')
            is_ds_related = path.index('datasets')
            if is_ds_related:
                ds_id = path[is_ds_related + 1]
            else:
                ds_id = request.data.get("dataset_id")
            if ds_id:
                q = session.execute(text("SELECT * FROM datasets WHERE id=:ds_id"), dict(ds_id=ds_id)).all()
                ds = q[0]._mapping
                if ds is not None:
                    resource = f"{ds["id"]}-{ds["name"]}"
            if Keycloak().is_token_valid(token, scope, resource):
                return func(*args, **kwargs)
            else:
                raise AuthenticationError("Token is not valid, or the user has not enough permissions.")
        return _auth
    return auth_wrapper


session = Session(engine)

def audit(func):
    @wraps(func)
    def _audit(*args, **kwargs):

        response_object, http_status = func(*args, **kwargs)

        if 'HTTP_X_FORWARDED_FOR' in request.environ:
            # if behind a proxy
            source_ip = request.environ['HTTP_X_FORWARDED_FOR']
        else:
            source_ip = request.environ['REMOTE_ADDR']

        token = Keycloak().decode_token(request.headers.get("Authorization", '').replace("Bearer ", ""))
        http_method = request.method
        http_endpoint = request.path
        api_function = func.__name__
        requested_by = token.get('sub')
        details = f"Requested by {token.get('sub')} - {token.get("email", '')}"
        to_save = Audit(source_ip, http_method, http_endpoint, requested_by, http_status, api_function, details)
        to_save.add()
        return response_object, http_status
    return _audit
