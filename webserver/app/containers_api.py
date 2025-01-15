"""
containers endpoints:
- GET /containers
- POST /containers
- PATCH /containers/<id>
- POST /registries
"""

from flask import Blueprint, request

from app.helpers.exceptions import DBRecordNotFoundError, InvalidRequest
from app.helpers.wrappers import audit, auth
from .models.container import Container
from .models.registry import Registry


bp = Blueprint('containers', __name__, url_prefix='/containers')


@bp.route('/', methods=['GET'])
@bp.route('', methods=['GET'])
@audit
def get_all_containers():
    """
    GET /containers endpoint.
        Returns the list of allowed containers
    """
    return Container.get_all(), 200


@bp.route('/', methods=['POST'])
@bp.route('', methods=['POST'])
@audit
@auth(scope='can_admin_dataset')
def add_image():
    """
    POST /containers endpoint.
    """
    body = Container.validate(request.json)
    # Make sure it doesn't exist already
    existing_image = Container.query.filter(
        Container.name == body["name"],
        Container.tag==body["tag"],
        Registry.url==body["registry"].url
    ).join(Registry).one_or_none()
    if existing_image:
        raise InvalidRequest(f"Image {body["name"]}:{body["tag"]} already exists in registry {body["registry"].url}")

    image = Container(**body)
    image.add()
    return {"id": image.id}, 201


@bp.route('/<int:image_id>', methods=['PATCH'])
@audit
@auth(scope='can_admin_dataset')
def patch_datasets_by_id_or_name(image_id:int=None):
    """
    PATCH /image/id endpoint. Edits an existing container image with a given id
    """
    image = Container.query.filter(Container.id == image_id).one_or_none()
    if not image:
        raise DBRecordNotFoundError(f"Container id: {image_id} not found")
    return {}, 204


@bp.route('/sync', methods=['POST'])
@audit
@auth(scope='can_admin_dataset')
def sync():
    """
    POST /containers/sync
        syncs up the list of available containers from the
        available registries and adds them to the DB table
        with both dashboard and ml flags to false, effectively
        making them not usable. To "enable" them one of those
        flags has to set to true. This is done to avoid undesirable
        or unintended containers to be used on a node.
    """
    return "ok", 200
