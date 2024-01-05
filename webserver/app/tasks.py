from flask import Blueprint

bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@bp.route('/service-info', methods=['GET'])
def get_service_info():
    return []

@bp.route('/', methods=['GET'])
def get_tasks():
    return []

@bp.route('/<task_id>', methods=['GET'])
def get_task_id(task_id):
    task = { "time": "123456", "event": "created", "id": task_id }
    return task

@bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_tasks(task_id):
    return "ok", 202

@bp.route('/', methods=['POST'])
def post_tasks():
    return "Created", 201

@bp.route('/validate', methods=['POST'])
def post_tasks_validate():
    return "Valid", 200
