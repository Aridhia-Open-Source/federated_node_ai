"""
admin endpoints:
- GET /audit
- POST /token_transfer
- POST /workspace/token
- POST /selection/beacon
"""

from flask import Blueprint, request
from sqlalchemy.orm import Session
from .helpers.db import engine
from .models.audit import Audit
from .helpers.query_filters import parse_query_params
from .helpers.audit import audit

bp = Blueprint('admin', __name__, url_prefix='/')
session = Session(engine)

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
    return "WIP", 200
