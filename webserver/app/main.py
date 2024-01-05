from flask import Blueprint, redirect, url_for

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/')
def index():
    return redirect(url_for('main.health_check'))

@bp.route("/health_check")
def health_check():
    return {
        "status": "ok"
    }
