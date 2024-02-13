"""
admin endpoints:
- GET /audit
- POST /token_transfer
- POST /workspace/token
- POST /selection/beacon
"""

from flask import Blueprint, request
from sqlalchemy.orm import scoped_session, sessionmaker

from .helpers.exceptions import DBRecordNotFoundError
from .helpers.wrappers import audit, auth
from .helpers.db import engine
from .helpers.query_filters import parse_query_params
from .helpers.query_validator import validate
from .models.audit import Audit
from .models.datasets import Datasets

bp = Blueprint('admin', __name__, url_prefix='/')
session_factory = sessionmaker(bind=engine)
session = scoped_session(session_factory)

@bp.route('/audit', methods=['GET'])
@auth(scope='can_do_admin')
def get_audit_logs():
    """
    GET /audit endpoint.
        Returns a list of audit entries
    """
    query = parse_query_params(Audit, request.args.copy())
    res = session.execute(query).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
    return res, 200

@bp.route('/token_transfer', methods=['POST'])
@audit
@auth(scope='can_transfer_token')
def post_transfer_token():
    """
    POST /token_transfer endpoint.
        Returns a user's token based on an approved DAR
    """
    return "WIP", 200

@bp.route('/workspace/token', methods=['POST'])
@audit
@auth(scope='can_transfer_token')
def post_workspace_transfer_token():
    """
    POST /workspace/token endpoint.
        Sends a user's token based on an approved DAR to an approved third-party
    """
    return "WIP", 200

@bp.route('/selection/beacon', methods=['POST'])
@audit
@auth(scope='can_access_dataset')
def select_beacon():
    """
    POST /selection/beacon endpoint.
        Checks the validity of a query on a dataset
    """
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
