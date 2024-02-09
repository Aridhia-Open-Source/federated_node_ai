import requests
from flask import Blueprint, redirect, url_for, request
from app.helpers.keycloak import Keycloak, URLS

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/')
def index():
    return redirect(url_for('main.health_check'))

@bp.route("/health_check")
def health_check():
    try:
        kc_request = requests.get(URLS["health_check"])
        kc_status = kc_request.ok
        status_text = "ok" if kc_request.ok else "non operational"
        code = 200 if kc_request.ok else 500
    except requests.exceptions.ConnectionError:
        kc_status = False
        status_text = "non operational"
        code = 500

    return {
        "status": status_text,
        "keycloak": kc_status
    }, code

@bp.route("/login", methods=['POST'])
def login():
    credentials = request.form.to_dict()
    return {
        "token": Keycloak().get_token(**credentials)
    }, 200
