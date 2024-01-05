import sqlalchemy
from flask import Blueprint, request
from sqlalchemy.orm import Session
from .exceptions import DBError, DBRecordNotFoundError
from .helpers.db import engine
from .models.datasets import Datasets

bp = Blueprint('datasets', __name__, url_prefix='/datasets')
session = Session(engine)

@bp.route('/', methods=['GET'])
def get_datasets():
    return {
        "datasets": Datasets.get_all()
    }

@bp.route('/', methods=['POST'])
def post_datasets():
    body = Datasets.validate(request.json)
    dataset = Datasets(body["name"], body["url"])
    try:
        session.add(dataset)
        session.commit()
    except sqlalchemy.exc.IntegrityError:
        raise DBError("Record already exists")

    return "ok", 201

@bp.route('/<dataset_id>', methods=['GET'])
def get_datasets_by_id(dataset_id):
    ds = session.get(Datasets, dataset_id)
    if ds is None:
        raise DBRecordNotFoundError(f"Dataset with id {dataset_id} does not exist")
    return Datasets.sanitized_dict(ds)

@bp.route('/<dataset_id>/catalogue', methods=['GET'])
def get_datasets_catalogue_by_id(dataset_id):
    dataset = Datasets.query.get(dataset_id)
    return {
        "datasets": []
    }

@bp.route('/<dataset_id>/dictionaries', methods=['GET'])
def get_datasets_dictionaries_by_id(dataset_id):
    return {
        "datasets": []
    }

@bp.route('/<dataset_id>/dictionaries/<table_id>', methods=['GET'])
def get_datasets_dictionaries_table_by_id(dataset_id, table_id):
    return {
        "datasets": []
    }
