import json
from kubernetes.client.exceptions import ApiException

from tests.fixtures.azure_cr_fixtures import *
from tests.fixtures.tasks_fixtures import *


class TestTaskResults:
    def test_get_results(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        results_job_mock,
        task_mock
    ):
        """
        A simple test with mocked PVs to test a successful result
        fetch
        """
        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_admin_header
        )
        assert response.status_code == 200
        assert response.content_type == "application/x-tar"

    def test_get_results_job_creation_failure(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        reg_k8s_client,
        results_job_mock,
        task_mock
    ):
        """
        Tests that the job creation to fetch results from a PV returns a 500
        error code
        """
        # Get results - creating a job fails
        reg_k8s_client["create_namespaced_job_mock"].side_effect = ApiException(status=500, reason="Something went wrong")

        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_admin_header
        )
        assert response.status_code == 400
        assert response.json["error"] == 'Failed to run pod: Something went wrong'

    def test_results_not_found_with_expired_date(
        self,
        simple_admin_header,
        client,
        task_mock
    ):
        """
        A task result are being deleted after a declared number of days.
        This test makes sure an error is returned as expected
        """
        task_mock.created_at -= timedelta(days=CLEANUP_AFTER_DAYS)
        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_admin_header
        )
        assert response.status_code == 500
        assert response.json["error"] == 'Tasks results are not available anymore. Please, run the task again'


class TestResultsReview:
    def test_default_review_status(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        task_mock,
        results_job_mock
    ):
        """
        Test to make sure the default value is None,
        and the correct task description is correct
        """
        response = client.get(
            f'/tasks/{task_mock.id}',
            headers=simple_admin_header
        )
        assert response.status_code == 200
        assert response.json["review_status"] == "Pending Review"

    def test_default_review_approved(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        simple_user_header,
        client,
        task_mock,
        results_job_mock,
        mock_patch_crd
    ):
        """
        Test to make sure the approval allows the user
        to retrieve their results
        """

        response = client.post(
            f'/tasks/{task_mock.id}/results/approve',
            headers=simple_admin_header
        )
        assert response.status_code == 202

        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_user_header
        )
        assert response.status_code == 200

    def test_default_review_pending(
        self,
        cr_client,
        registry_client,
        simple_user_header,
        client,
        results_job_mock,
        task_mock
    ):
        """
        Test to make sure the user can't fetch their results
        before the review took place
        """

        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_user_header
        )
        assert response.status_code == 400
        assert response.json["status"] == "Pending Review"

    def test_default_review_blocked(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        simple_user_header,
        client,
        results_job_mock,
        task_mock,
        mock_patch_crd
    ):
        """
        Test to make sure the user can't fetch their results
        before the review took place
        """
        response = client.post(
            f'/tasks/{task_mock.id}/results/block',
            headers=simple_admin_header
        )
        assert response.status_code == 202

        response = client.get(
            f'/tasks/{task_mock.id}/results',
            headers=simple_user_header
        )
        assert response.status_code == 400
        assert response.json["status"] == "Blocked Release"

    def test_review_task_not_found(
        self,
        cr_client,
        registry_client,
        simple_user_header,
        client,
        results_job_mock,
        task_mock
    ):
        """
        Trying to review an non-existing task should return 404
        """
        response = client.get(
            f'/tasks/{task_mock.id + 1}/results',
            headers=simple_user_header
        )
        assert response.status_code == 404
        assert response.json["error"] == f"Task with id {task_mock.id + 1} does not exist"

    def test_review_twice(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        results_job_mock,
        task_mock,
        mock_patch_crd
    ):
        """
        Tests that review can only happen once
        """
        response = client.post(
            f'/tasks/{task_mock.id}/results/block',
            headers=simple_admin_header
        )
        assert response.status_code == 202
        response = client.post(
            f'/tasks/{task_mock.id}/results/approve',
            headers=simple_admin_header
        )
        assert response.status_code == 400
        assert response.json['error'] == "Task has been already reviewed"

    def test_review_crd_patch_error(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        results_job_mock,
        task_mock,
        k8s_client
    ):
        """
        Tests that review can only happen once
        """
        k8s_client["patch_cluster_custom_object"].side_effect = ApiException(
            http_resp=Mock(
                status=500,
                reason="Error",
                data=json.dumps({
                    "details": {
                        "causes": [
                            {
                                "message": "Failed to patch the CRD"
                            }
                        ]
                    }
                })
            )
        )

        response = client.post(
            f'/tasks/{task_mock.id}/results/block',
            headers=simple_admin_header
        )
        assert response.status_code == 500
        assert response.json['error'] == "Could not activate automatic delivery"

    def test_review_crd_not_found(
        self,
        cr_client,
        registry_client,
        simple_admin_header,
        client,
        results_job_mock,
        task_mock,
        k8s_client
    ):
        """
        Tests that review can only happen once
        """
        k8s_client["get_cluster_custom_object"].side_effect = ApiException(
            http_resp=Mock(
                status=404,
                reason="Error",
                data=json.dumps({
                    "details": {
                        "causes": [
                            {
                                "message": "Not found"
                            }
                        ]
                    }
                })
            )
        )

        response = client.post(
            f'/tasks/{task_mock.id}/results/block',
            headers=simple_admin_header
        )
        assert response.status_code == 500
        assert response.json['error'] == "Failed to update result delivery"
