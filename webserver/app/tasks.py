"""
tasks-related endpoints:
- GET /tasks/service-info
- GET /tasks
- POST /tasks
- POST /tasks/validate
- GET /tasks/id
- POST /tasks/id/cancel
"""
from datetime import datetime
import sqlalchemy
from flask import Blueprint, request
from sqlalchemy import update

from .exceptions import DBRecordNotFoundError, DBError, InvalidRequest
from .helpers.audit import audit
from .helpers.db import db
from .helpers.query_filters import parse_query_params
from .helpers.query_validator import validate as validate_query
from .models.datasets import Datasets
from .models.tasks import Tasks

bp = Blueprint('tasks', __name__, url_prefix='/tasks')
session = db.session

@bp.route('/service-info', methods=['GET'])
@audit
def get_service_info():
    return "WIP", 200

@bp.route('/', methods=['GET'])
@audit
def get_tasks():
    query = parse_query_params(Tasks, request.args.copy())
    res = session.execute(query).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
    return res, 200

@bp.route('/<task_id>', methods=['GET'])
@audit
def get_task_id(task_id):
    task = session.get(Tasks, task_id)
    if task is None:
        raise DBRecordNotFoundError(f"Dataset with id {task_id} does not exist")
    return Tasks.sanitized_dict(task), 200

@bp.route('/<task_id>/cancel', methods=['POST'])
@audit
def cancel_tasks(task_id):
    task = session.get(Tasks, task_id)
    if task is None:
        raise DBRecordNotFoundError(f"Task with id {task_id} does not exist")
    # Should update
    query = update(Tasks).where(Tasks.id == task_id).values(
        status='cancelled',
        updated_at=datetime.now()
        )
    try:
        session.execute(query)
        session.commit()
        return Tasks.sanitized_dict(task), 201
    except:
        raise DBError(f"An error occurred while updating")

@bp.route('/', methods=['POST'])
@audit
def post_tasks():
    try:
        body = Tasks.validate(request.json)
        ds_id = body.pop("dataset_id")
        body["dataset"] = session.get(Datasets, ds_id)
        if body["dataset"] is None:
            raise DBRecordNotFoundError(f"Dataset {ds_id} not found")

        query = body.pop('use_query')
        if not validate_query(query, body["dataset"]):
            raise InvalidRequest("Query missing or misformed")

        task = Tasks(**body)
        if not task.can_image_be_found():
            return {
                "error": f"Image {task.docker_image} cannot be found in the registry"
            }, 400

        task.add()
        return {"task_id": task.id}, 201
    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        raise DBError("Record already exists")
    except KeyError:
        session.rollback()
        raise InvalidRequest("Missing field. Make sure \"catalogue\" and \"dictionary\" entries are there")
    except:
        session.rollback()
        raise

@bp.route('/validate', methods=['POST'])
@audit
def post_tasks_validate():
    return "WIP", 200
