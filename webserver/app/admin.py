"""
admin endpoints:
- GET /audit
- POST /token_transfer
- POST /workspace/token
- POST /selection/beacon
"""

from flask import Blueprint, request
from sqlalchemy.orm import scoped_session, sessionmaker

from .exceptions import DBRecordNotFoundError
from .helpers.audit import audit
from .helpers.db import engine
from .helpers.query_filters import parse_query_params
from .helpers.query_validator import validate
from .models.audit import Audit
from .models.datasets import Datasets

bp = Blueprint('admin', __name__, url_prefix='/')
session_factory = sessionmaker(bind=engine)
session = scoped_session(session_factory)

@bp.route('/audit', methods=['GET'])
def get_audit_logs():
    query = parse_query_params(Audit, request.args.copy())
    res = session.execute(query).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
    return res, 200

@bp.route('/token_transfer', methods=['POST'])
@audit
def post_transfer_token():
    return "WIP", 200

@bp.route('/workspace/token', methods=['POST'])
@audit
def post_workspace_transfer_token():
    return "WIP", 200

@bp.route('/selection/beacon', methods=['POST'])
@audit
def select_beacon():
    body = request.json.copy()
    dataset = session.get(Datasets, body['dataset_id'])
    if dataset is None:
        raise DBRecordNotFoundError(f"Dataset with id {body['dataset_id']} does not exist")

    if validate(body['query'], dataset):
        return {
            "query": body['query'],
            "result": "Ok"
        }, 200
    return {
        "query": body['query'],
        "result": "Invalid"
    }, 500
