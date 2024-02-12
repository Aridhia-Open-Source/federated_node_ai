"""
datasets-related endpoints:
- GET /datasets
- POST /datasets
- GET /datasets/id
- GET /datasets/id/catalogues
- GET /datasets/id/dictionaries
- GET /datasets/id/dictionaries/table_name
"""

import sqlalchemy
from flask import Blueprint, request
from sqlalchemy import select
from .helpers.exceptions import DBError, DBRecordNotFoundError, InvalidRequest
from .helpers.db import db
from .helpers.keycloak import Keycloak
from .helpers.wrappers import auth, audit
from .models.datasets import Datasets
from .models.catalogues import Catalogues
from .models.dictionaries import Dictionaries


bp = Blueprint('datasets', __name__, url_prefix='/datasets')
session = db.session

@bp.route('/', methods=['GET'])
@audit
@auth(scope='can_access_dataset')
def get_datasets():
    return {
        "datasets": Datasets.get_all()
    }, 200

@bp.route('/', methods=['POST'])
@audit
@auth(scope='can_admin_dataset')
def post_datasets():
    try:
        body = Datasets.validate(request.json)
        cata_body = body.pop("catalogue")
        dict_body = body.pop("dictionaries")
        dataset = Datasets(**body)
        cata_data = Catalogues.validate(cata_body)
        catalogue = Catalogues(dataset=dataset, **cata_data)

        kc_client = Keycloak()
        token_info = kc_client.decode_token(kc_client.get_token_from_headers(request.headers))
        dataset.add(commit=False, user_id=token_info['sub'])
        catalogue.add(commit=False)

        # Dictionaries should be a list of dict. If not raise an error and revert changes
        if not isinstance(dict_body, list):
            session.rollback()
            raise InvalidRequest("dictionaries should be a list.")

        for d in dict_body:
            dict_data = Dictionaries.validate(d)
            dictionary = Dictionaries(dataset=dataset, **dict_data)
            dictionary.add(commit=False)
        session.commit()
        return { "dataset_id": dataset.id }, 201

    except sqlalchemy.exc.IntegrityError as exc:
        session.rollback()
        raise DBError("Record already exists") from exc
    except KeyError as kexc:
        session.rollback()
        raise InvalidRequest(
            "Missing field. Make sure \"catalogue\" and \"dictionaries\" entries are there"
        ) from kexc
    except:
        session.rollback()
        raise

@bp.route('/<dataset_id>', methods=['GET'])
@audit
@auth(scope='can_access_dataset')
def get_datasets_by_id(dataset_id):
    ds = session.get(Datasets, dataset_id)
    if ds is None:
        raise DBRecordNotFoundError(f"Dataset with id {dataset_id} does not exist")
    return Datasets.sanitized_dict(ds), 200

@bp.route('/<dataset_id>/catalogue', methods=['GET'])
@audit
@auth(scope='can_access_dataset')
def get_datasets_catalogue_by_id(dataset_id):
    cata = select(Catalogues).where(Catalogues.dataset_id == dataset_id).limit(1)
    res = session.execute(cata).all()
    if res:
        res = res[0][0].sanitized_dict()
        return res, 200
    raise DBRecordNotFoundError(f"Dataset {dataset_id} has no catalogue.")

@bp.route('/<dataset_id>/dictionaries', methods=['GET'])
@audit
@auth(scope='can_access_dataset')
def get_datasets_dictionaries_by_id(dataset_id):
    dictionary = select(Dictionaries).where(Dictionaries.dataset_id == dataset_id)
    res = session.execute(dictionary).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
        return res, 200

    raise DBRecordNotFoundError(
        f"Dataset {dataset_id} has no dictionaries."
    )

@bp.route('/<dataset_id>/dictionaries/<table_name>', methods=['GET'])
@audit
@auth(scope='can_access_dataset')
def get_datasets_dictionaries_table_by_id(dataset_id, table_name):
    dictionary = select(Dictionaries).where(
        Dictionaries.dataset_id == dataset_id,
        Dictionaries.table_name == table_name
    )
    res = session.execute(dictionary).all()
    if res:
        res = [r[0].sanitized_dict() for r in res]
        return res, 200

    raise DBRecordNotFoundError(
        f"Dataset {dataset_id} has no dictionaries with table {table_name}."
    )
