import json
from sqlalchemy import select
from app.models.datasets import Datasets, Catalogues, Dictionaries
from tests.base_test import AbstractTest


class TestDatasets(AbstractTest):
    """
    Collection of tests for dataset-related endpoints
    """
    def setUp(self):
        super().setUp()
        self.expected_ds_entry = {
            "name": "TestDs",
            "host": "example.com",
            "id": 1
        }
        self.dataset_post_body = {
            "name": "TestDs",
            "host": "example.com",
            "catalogue": {
                "title": "test",
                "description": "test description"
            },
            "dictionaries": [{
                "table_name": "test",
                "description": "test description"
            }]
        }
        self.missing_dict_cata_message = "Missing field. Make sure \"catalogue\" and \"dictionary\" entries are there"

    def run_query(self, query):
        """
        Helper to run query through the ORM
        """
        return self.db_session.execute(query).all()

    def post_dataset(self, data_body={}, code=201):
        """
        Helper method that created a given dataset, if none specified
        uses self.dataset_post_body
        """
        if data_body == {}:
            data_body = self.dataset_post_body
        response = self.client.post(
            "/datasets/",
            data=json.dumps(data_body),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, code)
        return response

    def test_get_dataset_200(self):
        """
        /datasets GET returns a valid list
        """
        dataset = Datasets(name="TestDs", host="example.com")
        self.db_session.add(dataset)
        self.db_session.commit()

        response = self.client.get("/datasets/")

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json,
            {
                "datasets": [
                    self.expected_ds_entry
                ]
            }
        )

    def test_get_dataset_by_id_200(self):
        """
        /datasets/{id} GET returns a valid list
        """
        dataset = Datasets(name="TestDs", host="example.com")
        self.db_session.add(dataset)
        self.db_session.commit()

        ds_select = select(Datasets).where(Datasets.name == "TestDs").limit(1)
        ds = self.run_query(ds_select)[0][0]
        response = self.client.get(f"/datasets/{ds.id}")

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json,
            self.expected_ds_entry
        )

    def test_get_dataset_by_id_404(self):
        """
        /datasets/{id} GET returns a valid list
        """
        invalid_id = 100
        response = self.client.get(f"/datasets/{invalid_id}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data.decode(),
            f"Dataset with id {invalid_id} does not exist"
        )

    def test_post_dataset_is_successful(self):
        """
        /datasets POST is not successful
        """
        data_body = self.dataset_post_body.copy()
        self.post_dataset()

        query = self.run_query(select(Datasets).where(Datasets.name == data_body["name"]))
        self.assertEqual(len(query), 1)
        query = self.run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
        self.assertEqual(len(query), 1)
        for d in data_body["dictionaries"]:
            query = self.run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
            self.assertEqual(len(query), 1)

    def test_post_dataset_with_duplicate_dictionaries_fails(self):
        """
        /datasets POST is not successful
        """
        data_body = self.dataset_post_body.copy()
        data_body["dictionaries"].append(
            {
                "table_name": "test",
                "description": "test description"
            }
        )
        response = self.post_dataset(data_body, 500)
        self.assertEqual(response.data.decode(), 'Record already exists')

        # Make sure any db entry is created
        query = self.run_query(select(Datasets).where(Datasets.name == data_body["name"]))
        self.assertEqual(len(query), 0)
        query = self.run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
        self.assertEqual(len(query), 0)
        for d in data_body["dictionaries"]:
            query = self.run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
            self.assertEqual(len(query), 0)

    def test_post_datasets_with_same_dictionaries_succeeds(self):
        """
        /datasets POST is successful with same catalogues and dictionaries
        """
        data_body = self.dataset_post_body.copy()
        self.post_dataset()

        # Make sure db entries are created
        query = self.run_query(select(Datasets).where(Datasets.name == data_body["name"]))
        self.assertEqual(len(query), 1)
        query = self.run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
        self.assertEqual(len(query), 1)
        for d in data_body["dictionaries"]:
            query = self.run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
            self.assertEqual(len(query), 1)

        # Creating second DS
        data_body["name"] = "Another DS"
        self.post_dataset(data_body)

        # Make sure any db entry is created
        query = self.run_query(select(Datasets).where(Datasets.name == data_body["name"]))
        self.assertEqual(len(query), 1)
        query = self.run_query(select(Catalogues).where(Catalogues.title == data_body["catalogue"]["title"]))
        self.assertEqual(len(query), 2)
        for d in data_body["dictionaries"]:
            query = self.run_query(select(Dictionaries).where(Dictionaries.table_name == d["table_name"]))
            self.assertEqual(len(query), 2)

    def test_post_dataset_with_catalogue(self):
        """
        /datasets POST with catalogue but no dictionary is not successful
        """
        data_body = self.dataset_post_body.copy()
        data_body.pop("dictionaries")
        response = self.post_dataset(data_body, 500)
        self.assertEqual(response.data.decode(), self.missing_dict_cata_message)

    def test_post_dataset_with_dictionaries(self):
        """
        /datasets POST with dictionary but no catalogue is not successful
        """
        data_body = self.dataset_post_body.copy()
        data_body.pop("catalogue")
        response = self.post_dataset(data_body, 500)
        self.assertEqual(response.data.decode(), self.missing_dict_cata_message)
