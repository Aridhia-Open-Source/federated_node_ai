import json
from sqlalchemy import select

from app.helpers.db import db
from app.models.datasets import Datasets
from app.models.catalogues import Catalogues
from app.models.dictionaries import Dictionaries
from tests.conftest import sample_ds_body

missing_dict_cata_message = {"error": "Missing field. Make sure \"catalogue\" and \"dictionaries\" entries are there"}

def run_query(query):
    """
    Helper to run query through the ORM
    """
    return db.session.execute(query).all()

def post_dataset(client, headers, data_body=sample_ds_body, code=201):
    """
    Helper method that created a given dataset, if none specified
    uses dataset_post_body
    """
    response = client.post(
        "/datasets/",
        data=json.dumps(data_body),
        headers=headers
    )
    assert response.status_code == code, response.data.decode()
    return response.json

def test_get_all_datasets(simple_admin_header, user_uuid, client, k8s_client, k8s_config):
    dataset = Datasets(name="TestDs", host="db", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    expected_ds_entry = {
        "id": dataset.id,
        "name": "TestDs",
        "host": "db",
        "port": 5432
    }

    response = client.get("/datasets/", headers=simple_admin_header)

    assert response.status_code == 200
    assert response.json == {
        "datasets": [
            expected_ds_entry
        ]
    }

def test_get_dataset_by_id_200(simple_admin_header, user_uuid, client, k8s_config, k8s_client):
    """
    /datasets/{id} GET returns a valid list
    """
    dataset = Datasets(name="TestDs2", host="db_host", password='pass', username='user')
    dataset.add(user_id=user_uuid)
    expected_ds_entry = {
        "id": dataset.id,
        "name": "TestDs2",
        "host": "db_host",
        "port": 5432
    }
    response = client.get(f"/datasets/{dataset.id}", headers=simple_admin_header)
    assert response.status_code == 200
    assert response.json == expected_ds_entry

def test_get_dataset_by_id_404(simple_admin_header, client):
    """
    /datasets/{id} GET returns a valid list
    """
    invalid_id = 100
    response = client.get(f"/datasets/{invalid_id}", headers=simple_admin_header)

    assert response.status_code == 404
    assert response.json == {"error": f"Dataset with id {invalid_id} does not exist"}

def test_post_dataset_is_successful(post_json_admin_header, client, k8s_client, k8s_config, dataset_post_body):
    """
    /datasets POST is not successful
    """
    data_body = dataset_post_body.copy()
    data_body['name'] = 'TestDs78'
    post_dataset(client, post_json_admin_header, data_body)

    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query)== 1
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query)== 1

def test_post_dataset_with_duplicate_dictionaries_fails(post_json_admin_header, client, k8s_client, k8s_config,dataset_post_body):
    """
    /datasets POST is not successful
    """
    data_body = dataset_post_body.copy()
    data_body['name'] = 'TestDs22'
    data_body["dictionaries"].append(
        {
            "table_name": "test",
            "description": "test description"
        }
    )
    response = post_dataset(client, post_json_admin_header, data_body, 500)
    assert response == {'error': 'Record already exists'}

    # Make sure any db entry is created
    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 0
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 0
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 0

def test_post_datasets_with_same_dictionaries_succeeds(post_json_admin_header, client, k8s_client, k8s_config, dataset_post_body):
    """
    /datasets POST is successful with same catalogues and dictionaries
    """
    data_body = dataset_post_body.copy()
    data_body['name'] = 'TestDs23'
    post_dataset(client, post_json_admin_header, data_body)

    # Make sure db entries are created
    query = run_query(select(Datasets).where(Datasets.name == data_body['name']))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 1
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 1

    # Creating second DS
    data_body["name"] = "Another DS"
    ds_resp = post_dataset(client, post_json_admin_header, data_body)

    # Make sure any db entry is created
    query = run_query(select(Datasets).where(Datasets.id == ds_resp["dataset_id"]))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 2
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 2

def test_post_dataset_with_catalogue(post_json_admin_header, client, dataset_post_body):
    """
    /datasets POST with catalogue but no dictionary is not successful
    """
    data_body = dataset_post_body.copy()
    data_body.pop("dictionaries")
    response = post_dataset(client, post_json_admin_header, data_body, 500)
    assert response == missing_dict_cata_message

def test_post_dataset_with_dictionaries(post_json_admin_header, query_validator, client, dataset_post_body):
    """
    /datasets POST with dictionary but no catalogue is not successful
    """
    data_body = dataset_post_body.copy()
    data_body.pop("catalogue")
    response = post_dataset(client, post_json_admin_header, data_body, 500)
    assert response == missing_dict_cata_message
