"""
request-related endpoints:
- GET /requests
- POST /requests
- GET /code/approve
"""

from flask import Blueprint
from .helpers.audit import audit

bp = Blueprint('requests', __name__, url_prefix='/requests')


@bp.route('/', methods=['GET'])
@audit
def get_requests():
    return "WIP", 200

@bp.route('/', methods=['POST'])
@audit
def post_requests():
    return "WIP", 200

@bp.route('/<code>/approve', methods=['POST'])
@audit
def post_approve_requests(code):
    return "WIP", 200
