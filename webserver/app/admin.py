from flask import Blueprint
from sqlalchemy.orm import Session
from app.helpers.db import engine
from app.models.audit import Audit

bp = Blueprint('admin', __name__, url_prefix='/')
session = Session(engine)

@bp.route('/audit', methods=['GET'])
def get_audit_logs():
    return Audit.get_all(), 200

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
