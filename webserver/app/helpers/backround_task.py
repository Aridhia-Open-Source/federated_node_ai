import logging
import requests
import threading

from app.helpers.const import RESULTS_PATH, SLM_BACKEND_URL


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

    def run(self, *args, **kwargs):
        resp = requests.post(
            f"{SLM_BACKEND_URL}/ask",
            data={"message": self.query,"file": open(f"{RESULTS_PATH}/fetched-data/fetched-data/{self.file_name}.csv", "rb")}
        )
        logger.info("Status: %s", resp.status_code)
        if not resp.ok:
            logger.error(resp.text)
