from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/')

@bp.route('/audit', methods=['GET'])
def get_audit_logs():
    return [
        { "time": "123456", "event": "Dataset created" }
    ]

@bp.route('/token_transfer', methods=['POST'])
def post_transfer_token():
    return "Tranfer Submitted", 200

@bp.route('/workspace/token', methods=['POST'])
def post_workspace_transfer_token():
    return "Tranfer Successful", 200

@bp.route('/selection/beacon', methods=['POST'])
def select_beacon():
    return {
        "results": []
    }
