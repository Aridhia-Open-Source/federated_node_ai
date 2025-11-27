"""
A collection of general use endpoints
These won't have any restrictions and won't go through
    Keycloak for token validation.
"""
import json
from http import HTTPStatus
import logging
import requests
from flask import Blueprint, redirect, url_for, request
from kubernetes.client import ApiException
from kubernetes.watch import Watch

from app.helpers.const import TASK_NAMESPACE
from app.helpers.kubernetes import KubernetesClient
from app.helpers.keycloak import Keycloak, URLS
from app.helpers.exceptions import InvalidRequest, AuthenticationError
from app.helpers.rabbit import send_json_message
from app.helpers.fetch_data_container import FetchDataContainer
from app.models.dataset import Dataset
from app.models.request import Request
from app.helpers.wrappers import async_audit, async_auth


logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/')
def index():
    """
    GET / endpoint.
        Redirects to /health_check
    """
    return redirect(url_for('main.health_check'))

@bp.route("/ready_check")
def ready_check():
    """
    GET /ready_check endpoint
        Mostly to tell k8s Flask has started
    """
    return {"status": "ready"}, HTTPStatus.OK

@bp.route("/health_check")
def health_check():
    """
    GET /health_check endpoint
        Checks the connection to keycloak and returns a jsonized summary
    """
    try:
        kc_request = requests.get(URLS["health_check"], timeout=30)
        kc_status = kc_request.ok
        status_text = "ok" if kc_request.ok else "non operational"
        code = HTTPStatus.OK if kc_request.ok else HTTPStatus.BAD_GATEWAY
    except requests.exceptions.ConnectionError:
        kc_status = False
        status_text = "non operational"
        code = HTTPStatus.BAD_GATEWAY

    return {
        "status": status_text,
        "keycloak": kc_status
    }, code

@bp.route("/login", methods=['POST'])
def login():
    """
    POST /login endpoint.
        Given a form, logs the user in, returning a refresh_token from Keycloak
    """
    credentials = request.form.to_dict()
    return {
        "token": Keycloak().get_token(**credentials)
    }, HTTPStatus.OK

@bp.route("/ask", methods=["POST"])
@async_audit
@async_auth(scope='can_do_admin')
# @async_auth(scope='can_send_nlq')
async def ask():
    """
    POST /ask endpoint
        Given a prompt, send it to the ollama API interface
        return its response or graciously handle the errors
    """
    query: str | None = request.json.get("question")
    table: str | None = request.json.get("table")
    if not query and not table:
        raise InvalidRequest("Question and table are mandatory fields", 400)

    kc_client = Keycloak()
    user_token = Keycloak.get_token_from_headers()
    user_id = kc_client.decode_token(user_token).get('sub')

    if kc_client.is_user_admin(user_token):
        dataset = Dataset.get_dataset_by_name_or_id(**request.json.get("dataset"))
    else:
        project = request.headers.get("project-name")
        dataset: Dataset = Request.get_active_project(project, user_id).dataset

    fdc = FetchDataContainer(
        dataset=dataset, table=table
    )

    v1 = KubernetesClient()
    data_pod = fdc.get_full_pod_definition()
    try:
        v1.create_namespaced_pod(
            namespace=TASK_NAMESPACE,
            body=data_pod,
            pretty='true'
        )
    except ApiException as e:
        logger.error(json.loads(e.body))
        raise InvalidRequest(f"Failed to run pod: {e.reason}") from e

    # check when the task is done, maybe with k8s watch instead
    logging.info("Fetching data, waiting for %s to complete", data_pod.metadata.name)
    watcher = Watch()
    for pod in watcher.stream(
        v1.list_namespaced_pod,
        namespace=TASK_NAMESPACE,
        label_selector=f"pod={fdc.pod_name}"
    ):
        if pod["object"].metadata.name == data_pod.metadata.name:
            logging.info("Found pod %s", pod["object"].metadata.name)
            logging.info("Status %s", pod["object"].status.phase)
            match pod["object"].status.phase:
                case "Failed":
                    logger.error(v1.read_namespaced_pod_log(
                        fdc.pod_name, timestamps=True,
                        namespace=TASK_NAMESPACE,
                        container="fetch-data"
                    ).splitlines())
                    raise InvalidRequest("Failed to fetch data", 500)
                case "Succeeded":
                    # Send to queue
                    send_json_message({
                        "query": query,
                        "file_name": dataset.get_creds_secret_name(),
                        "dataset_name": dataset.name,
                        "user_id": user_id
                    })
                    return {
                        "message": "Request submitted successfully. Results will be delivered back automatically"
                    }, HTTPStatus.OK
                case _:
                    pass

@bp.route("/refresh_token", methods=['POST'])
def refresh_token():
    """
    POST /refresh_token endpoint.
        Given a token, exchanges it for a new one. Returns the same
        response as /login
    """
    token = Keycloak.get_token_from_headers()
    kc_client = Keycloak()
    if not kc_client.is_token_valid(token, resource=None, scope=None, with_permissions=False):
        raise AuthenticationError()

    return {
        "token": kc_client.exchange_global_token(token, "refresh_token")
    }, HTTPStatus.OK
