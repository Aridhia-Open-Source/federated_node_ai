import base64
import logging
import os
import subprocess
import requests
import threading
import uuid

from app.helpers.const import RESULTS_PATH, SLM_BACKEND_URL
from app.helpers.exceptions import InvalidRequest
from app.helpers.kubernetes import KubernetesClient


logger: logging.Logger = logging.getLogger('background_tasks')
logger.setLevel(logging.INFO)


class BackgroundTasks(threading.Thread):
    """
    Simple class for creating a Thread with the API
    request to the SLM_BACKEND_URL. This can theoretically
    take a long time and waiting for it would timeout the
    client request.
    """

    def __init__(self, group = None, target = None, name = None, args = ..., kwargs = None, *, daemon = None):
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.query: str = kwargs.pop("query")
        self.file_name: str = kwargs.pop("file_name")
        self.dataset_name: str = kwargs.pop("dataset_name")
        self.user_id: str = kwargs.pop("user_id")
        self.dataset_file_name: str = f"{RESULTS_PATH}/fetched-data/{self.file_name}.csv"
        self.expected_file_name: str = f"{RESULTS_PATH}/{self.dataset_name}-{uuid.uuid4()}.zip"

    def run(self, *args, **kwargs):
        resp = requests.post(
            f"{SLM_BACKEND_URL}/ask",
            data={
                "message": self.query,
                "dataset_name": self.dataset_name,
                "user_id": self.user_id,
            }, files={"file": open(self.dataset_file_name, "rb")}
        )
        logger.info("Status: %s", resp.status_code)
        if not resp.ok:
            logger.error(resp.text)
            raise InvalidRequest("The query failed to execute")

        # Save the file
        with open(self.expected_file_name, "wb") as file:
            file.write(resp.content)

        # Deliver results
        auth_secret = KubernetesClient().get_secret_by_label(
            namespace="default", label=f"url={os.getenv("DELIVERY_URL")}"
        )
        creds = base64.b64decode(
            auth_secret.data["auth"].encode()
        ).decode()
        out = subprocess.run(
            ["azcopy", "copy", self.expected_file_name, creds],
            capture_output=True,
            check=False
        )
        if out.stderr:
            logger.error(out.stderr)
            raise InvalidRequest(
                "Something went wrong with the result push"
            )
        logger.info(out.stdout)
        os.remove(self.expected_file_name)
