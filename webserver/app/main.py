from flask import Blueprint, redirect, url_for, request
from app.helpers.keycloak import Keycloak

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/')
def index():
    return redirect(url_for('main.health_check'))

@bp.route("/health_check")
def health_check():
    return {
        "status": "ok"
    }

@bp.route("/login", methods=['POST'])
def login():
    credentials = request.form.to_dict()
    return {
        "token": Keycloak().get_token(**credentials)
    }, 200
