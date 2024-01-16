from functools import wraps
from flask import request

from app.models.audit import Audit
from sqlalchemy.orm import Session
from .db import engine

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

        http_method = request.method
        http_endpoint = request.path
        api_function = func.__name__
        details = None
        to_save = Audit(source_ip, http_method, http_endpoint, http_status, api_function, details)
        to_save.add()
        return response_object, http_status
    return _audit
