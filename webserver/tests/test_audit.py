from sqlalchemy import select
from app.helpers.db import db
from app.models.audit import Audit

def test_get_audit_events(client):
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
        'details': None,
        'endpoint': '/datasets/',
        'http_method': 'GET',
        'ip_address':
        '127.0.0.1',
        'status_code': 200
    }.items()
