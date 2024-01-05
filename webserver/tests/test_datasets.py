from sqlalchemy import select
from app.models.datasets import Datasets
from tests.base_test import AbstractTest


class TestDatasets(AbstractTest):
    def setUp(self):
        super().setUp()
        self.expected_ds_entry = {
            "name": "TestDs",
            "host": "example.com",
            "id": 1,
            "catalogue_id": None,
            "dictionary_id": None
        }


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

        ds_select = select(Datasets).where(Datasets.name == "TestDs").limit(1)#Datasets.query.filter_by(name="TestDs")
        ds = self.db_session.execute(ds_select).scalar_one()
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
        response = self.client.get(f"/datasets/100")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data.decode(),
            "Dataset with id 100 does not exist"
        )
