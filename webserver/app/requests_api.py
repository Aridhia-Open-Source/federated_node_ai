"""
request-related endpoints:
- GET /requests
- POST /requests
- GET /code/approve
"""
import json
from flask import Blueprint, request
from app.helpers.exceptions import DBRecordNotFoundError, InvalidRequest
from app.helpers.wrappers import audit, auth
from app.helpers.db import db
from app.models.datasets import Datasets
from app.models.requests import Requests
from app.helpers.query_filters import parse_query_params

bp = Blueprint('requests', __name__, url_prefix='/requests')
session = db.session

@bp.route('/', methods=['GET'])
@audit
@auth(scope='can_admin_request')
def get_requests():
    """
    GET /requests/ endpoint. Gets a list of Data Access Requests
    """
    query = parse_query_params(Requests, request.args.copy())
    res = session.execute(query).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
    return res, 200

@bp.route('/', methods=['POST'])
@audit
@auth(scope='can_send_request')
def post_requests():
    """
    POST /requests/ endpoint. Creates a new Data Access Request
    """
    try:
        body = request.json
        if 'email' not in body["requested_by"].keys():
            raise InvalidRequest("Missing email from requested_by field")

        body["requested_by"] = json.dumps(body["requested_by"])
        ds_id = body.pop("dataset_id")
        body["dataset"] = session.get(Datasets, ds_id)
        if body["dataset"] is None:
            raise DBRecordNotFoundError(f"Dataset {ds_id} not found")

        req_attributes = Requests.validate(body)
        req = Requests(**req_attributes)
        req.add()
        return {"request_id": req.id}, 201
    except KeyError as kexc:
        session.rollback()
        raise InvalidRequest(
            "Missing field. Make sure \"catalogue\" and \"dictionary\" entries are there"
        ) from kexc
    except:
        session.rollback()
        raise

@bp.route('/<code>/approve', methods=['POST'])
@audit
@auth(scope='can_admin_request')
def post_approve_requests(code):
    """
    POST /requests/code/approve endpoint. Approves a pending Data Access Request
    """
    dar = session.get(Requests, code)
    if dar is None:
        raise DBRecordNotFoundError(f"Data Access Request {code} not found")

    if dar.status == dar.STATUSES["approved"]:
        return {"message": "Request alread approved"}, 200

    if dar.status == dar.STATUSES["rejected"]:
        raise InvalidRequest("Request was rejected already")

    user_info = dar.approve()
    return user_info, 201
