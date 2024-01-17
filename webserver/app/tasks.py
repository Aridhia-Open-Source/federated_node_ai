"""
tasks-related endpoints:
- GET /tasks/service-info
- GET /tasks
- POST /tasks
- POST /tasks/validate
- GET /tasks/id
- POST /tasks/id/cancel
"""

from flask import Blueprint
from .helpers.audit import audit

bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@bp.route('/service-info', methods=['GET'])
@audit
def get_service_info():
    return "WIP", 200

@bp.route('/', methods=['GET'])
@audit
def get_tasks():
    return "WIP", 200

@bp.route('/<task_id>', methods=['GET'])
@audit
def get_task_id(task_id):
    return "WIP", 200

@bp.route('/<task_id>/cancel', methods=['POST'])
@audit
def cancel_tasks(task_id):
    return "WIP", 200

@bp.route('/', methods=['POST'])
@audit
def post_tasks():
    return "WIP", 200

@bp.route('/validate', methods=['POST'])
@audit
def post_tasks_validate():
    return "WIP", 200
