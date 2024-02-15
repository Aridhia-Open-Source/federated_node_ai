from app.models.audit import Audit

def test_filter_by_date(
        client,
        simple_admin_header,
):
    """
    Testing the efficacy of filtering by date fields
        - __lte => less than or equal
        - __gte => greater than or equal
        - =     => equal
        - __eq  => equal
        - __gt  => greater than
        - __lt  => less than
        - __ne  => not equal
    """
    client.get('/datasets/', headers=simple_admin_header)
    client.get('/datasets/', headers=simple_admin_header)
    client.get('/datasets/', headers=simple_admin_header)

    date_filter = Audit.get_all()[1]['event_time']
    filters = {
        '=': 1,
        '__lte': 2,
        '__gte': 2,
        '__eq': 1,
        '__gt': 1,
        '__lt': 1,
        '__ne': 2
    }
    for fil, expected_results in filters.items():
        resp = client.get(f"/audit?event_time{fil}={date_filter}", headers=simple_admin_header)
        assert resp.status_code == 200
        assert len(resp.json) == expected_results
