from datetime import datetime
from sqlalchemy import select
from app.helpers.db import db
from app.models.audit import Audit
from app.models.datasets import Datasets


def test_get_audit_events(simple_admin_header, client, user_uuid):
    """
    Test that after a simple GET call we have an audit entry
    """
    r = client.get("/datasets/", headers=simple_admin_header)
    assert r.status_code == 200, r.text
    list_audit = db.session.execute(select(Audit)).all()
    assert len(list_audit) > 0
    response = client.get("/audit", headers=simple_admin_header)

    assert response.status_code == 200

    # Check if the expected result is a subset of the actual response
    # We do not check the entire dict due to the datetime and id
    assert response.json[0].items() >= {
        'api_function': 'get_datasets',
        'details': f'Requested by {user_uuid} - ',
        'endpoint': '/datasets/',
        'requested_by': user_uuid,
        'http_method': 'GET',
        'ip_address': '127.0.0.1',
        'status_code': 200
    }.items()

def test_get_audit_events_not_by_standard_users(
        simple_user_header,
        client
    ):
    """
    Test that the endpoint returns 401 for non-admin users
    """
    response = client.get("/audit", headers=simple_user_header)
    assert response.status_code == 401

def test_get_filtered_audit_events(simple_admin_header, client):
    """
    Test that after a simple GET call we have an audit entry
    """
    client.get("/datasets/", headers=simple_admin_header)
    date_filter = datetime.now().date()
    response = client.get(f"/audit?event_time__lte={date_filter}", headers=simple_admin_header)

    assert response.status_code == 200, response.json
    assert len(response.json) == 0

def test_beacon_available_to_admin(
        client,
        post_json_admin_header,
        user_uuid,
        mocker,
        k8s_client,
        k8s_config
):
    """
    Test that the beacon endpoint is accessible to admin users
    """
    mocker.patch(
        'app.admin_api.validate',
        return_value=True,
        autospec=True
    )
    dataset = Datasets(name="TestDs", host="db_host", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    response = client.post(
        "/selection/beacon",
        json={
            "query": "SELECT * FROM films2",
            "dataset_id": dataset.id
        },
        headers=post_json_admin_header
    )
    assert response.status_code == 200
    assert response.json['result'] == 'Ok'

def test_beacon_available_to_admin_invalid_query(
        client,
        post_json_admin_header,
        user_uuid,
        mocker,
        k8s_client,
        k8s_config
):
    """
    Test that the beacon endpoint is accessible to admin users
    """
    mocker.patch(
        'app.admin_api.validate',
        return_value=False,
        autospec=True
    )
    dataset = Datasets(name="TestDs", host="db_host", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    response = client.post(
        "/selection/beacon",
        json={
            "query": "SELECT * FROM films2",
            "dataset_id": dataset.id
        },
        headers=post_json_admin_header
    )
    assert response.status_code == 500
    assert response.json['result'] == 'Invalid'

def test_token_transfer_admin(
        client,
        simple_admin_header
):
    """
    Test token transfer is accessible by admin users
    """
    response = client.post(
        "/token_transfer",
        headers=simple_admin_header
    )
    assert response.status_code == 200

def test_token_transfer_standard_user(
        client,
        simple_user_header
):
    """
    Test token transfer is accessible by admin users
    """
    response = client.post(
        "/token_transfer",
        headers=simple_user_header
    )
    assert response.status_code == 401

def test_workspace_token_transfer_admin(
        client,
        simple_admin_header
):
    """
    Test token transfer is not accessible by non-admin users
    """
    response = client.post(
        "/workspace/token",
        headers=simple_admin_header
    )
    assert response.status_code == 200

def test_workspace_token_transfer_standard_user(
        client,
        simple_user_header
):
    """
    Test workspace token transfer is not accessible by non-admin users
    """
    response = client.post(
        "/workspace/token",
        headers=simple_user_header
    )
    assert response.status_code == 401
