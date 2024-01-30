import pytest
from datetime import datetime
from sqlalchemy import select
from app.helpers.db import db
from app.models.audit import Audit
from tests.conftest import good_tokens, query_validator

def test_get_audit_events(client, user_uuid):
    """
    Test that after a simple GET call we have an audit entry
    """
    client.get("/datasets/")
    list_audit = db.session.execute(select(Audit)).all()
    assert len(list_audit) > 0
    response = client.get("/audit")

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

def test_get_filtered_audit_events(client):
    """
    Test that after a simple GET call we have an audit entry
    """
    client.get("/datasets/")
    date_filter = datetime.now().date()
    response = client.get(f"/audit?event_time__lte={date_filter}")

    assert response.status_code == 200
    assert len(response.json) == 0
