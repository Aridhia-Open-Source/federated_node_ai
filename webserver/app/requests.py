from flask import Blueprint

bp = Blueprint('requests', __name__, url_prefix='/requests')


@bp.route('/', methods=['GET'])
def get_requests():
    return {
        "requests": []
    }

@bp.route('/', methods=['POST'])
def post_requests():
    return "ok", 201

@bp.route('/<code>/approve', methods=['POST'])
def post_approve_requests(code):
    return "ok", 201
