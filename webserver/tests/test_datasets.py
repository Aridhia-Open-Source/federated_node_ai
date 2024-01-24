import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.datasets import Datasets, Catalogues, Dictionaries


dataset_post_body = {
    "name": "TestDs",
    "host": "db",
    "port": 5432,
    "username": "Username",
    "password": "pass",
    "catalogue": {
        "title": "test",
        "description": "test description"
    },
    "dictionaries": [{
        "table_name": "test",
        "description": "test description"
    }]
}
missing_dict_cata_message = {"error": "Missing field. Make sure \"catalogue\" and \"dictionary\" entries are there"}

def run_query(query):
    """
    Helper to run query through the ORM
    """
    return Session().execute(query).all()

def post_dataset(client, data_body={}, code=201):
    """
    Helper method that created a given dataset, if none specified
    uses dataset_post_body
    """
    if data_body == {}:
        data_body = dataset_post_body
    response = client.post(
        "/datasets/",
        data=json.dumps(data_body),
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == code
    return response

def test_get_all_datasets(client, k8s_client, k8s_config):
    dataset = Datasets(name="TestDs", host="db", password='pass', username='user')
    dataset.add()
    expected_ds_entry = {
        "id": dataset.id,
        "name": "TestDs",
        "host": "db",
        "port": 5432
    }

    response = client.get("/datasets/")

    assert response.status_code == 200
    assert response.json == {
        "datasets": [
            expected_ds_entry
        ]
    }

def test_get_dataset_by_id_200(client, k8s_config, k8s_client):
    """
    /datasets/{id} GET returns a valid list
    """
    dataset = Datasets(name="TestDs", host="example.com", password='pass', username='user')
    dataset.add()
    expected_ds_entry = {
        "id": dataset.id,
        "name": "TestDs",
        "host": "example.com",
        "port": 5432
    }
    response = client.get(f"/datasets/{dataset.id}")
    print(response)
    assert response.status_code == 200
    assert response.json == {
        "datasets": [
            expected_ds_entry
        ]
    }

def test_get_dataset_by_id_404(client):
    """
    /datasets/{id} GET returns a valid list
    """
    invalid_id = 100
    response = client.get(f"/datasets/{invalid_id}")

    assert response.status_code == 404
    assert response.json == {"error": f"Dataset with id {invalid_id} does not exist"}

def test_post_dataset_is_successful(client, k8s_client, k8s_config):
    """
    /datasets POST is not successful
    """
    data_body = dataset_post_body.copy()
    post_dataset(client)

    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query)== 1
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query)== 1

def test_post_dataset_with_duplicate_dictionaries_fails(client, k8s_client, k8s_config):
    """
    /datasets POST is not successful
    """
    data_body = dataset_post_body.copy()
    data_body["dictionaries"].append(
        {
            "table_name": "test",
            "description": "test description"
        }
    )
    response = post_dataset(client, data_body, 500)
    assert response.data.decode() == 'Record already exists'

    # Make sure any db entry is created
    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 0
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 0
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 0

def test_post_datasets_with_same_dictionaries_succeeds(client, k8s_client, k8s_config):
    """
    /datasets POST is successful with same catalogues and dictionaries
    """
    data_body = dataset_post_body.copy()
    post_dataset(client)

    # Make sure db entries are created
    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 1
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 1

    # Creating second DS
    data_body["name"] = "Another DS"
    post_dataset(client, data_body)

    # Make sure any db entry is created
    query = run_query(select(Datasets).where(Datasets.name == data_body["name"]))
    assert len(query) == 1
    query = run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
    assert len(query) == 2
    for d in data_body["dictionaries"]:
        query = run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
        assert len(query) == 2

def test_post_dataset_with_catalogue(client):
    """
    /datasets POST with catalogue but no dictionary is not successful
    """
    data_body = dataset_post_body.copy()
    data_body.pop("dictionaries")
    response = post_dataset(client, data_body, 500)
    assert response.json == missing_dict_cata_message

def test_post_dataset_with_dictionaries(client):
    """
    /datasets POST with dictionary but no catalogue is not successful
    """
    data_body = dataset_post_body.copy()
    data_body.pop("catalogue")
    response = post_dataset(client, data_body, 500)
    assert response.json == missing_dict_cata_message
