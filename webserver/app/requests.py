"""
request-related endpoints:
- GET /requests
- POST /requests
- GET /code/approve
"""
import sqlalchemy
from flask import Blueprint, request
from .exceptions import DBRecordNotFoundError, DBError, InvalidRequest
from .helpers.audit import audit
from .helpers.db import db
from .models.datasets import Datasets
from .models.requests import Requests
from .helpers.query_filters import parse_query_params

bp = Blueprint('requests', __name__, url_prefix='/requests')
session = db.session

@bp.route('/', methods=['GET'])
@audit
def get_requests():
    query = parse_query_params(Requests, request.args.copy())
    res = session.execute(query).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
    return res, 200

@bp.route('/', methods=['POST'])
@audit
def post_requests():
    try:
        body = request.json
        ds_id = body.pop("dataset_id")
        body["dataset"] = session.get(Datasets, ds_id)
        if body["dataset"] is None:
            raise DBRecordNotFoundError(f"Dataset {ds_id} not found")

        req_attributes = Requests.validate(body)
        req = Requests(**req_attributes)
        req.add()
        return {"request_id": req.id}, 201
    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        raise DBError("Record already exists")
    except KeyError:
        session.rollback()
        raise InvalidRequest("Missing field. Make sure \"catalogue\" and \"dictionary\" entries are there")
    except:
        session.rollback()
        raise

@bp.route('/<code>/approve', methods=['POST'])
@audit
def post_approve_requests(code):
    dar = session.get(Requests, code)
    if dar is None:
        raise DBRecordNotFoundError(f"Data Access Request {code} not found")
    query = sqlalchemy.update(Requests).where(Requests.id == code).values(status='approved')
    session.execute(query)
    session.commit()
    return "ok", 201
