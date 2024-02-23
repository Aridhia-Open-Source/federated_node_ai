from base64 import b64encode
import requests
from app.helpers.exceptions import AcrException

class ACRClient:
    """
    Class to handle a set of ACR actions
    """
    def __init__(self, url:str, username:str, password:str) -> None:
        self.url = url
        self.username = username
        self.password = password
        self.b64_auth = b64encode(f"{username}:{password}".encode()).decode()

    def login(self, image:str):
        """
        Get an access token from the ACR, works on Azure, should be double checked
        on other services
        """
        response_auth = requests.get(
            f"https://{self.url}/oauth2/token?service={self.url}&scope=repository:{image}:metadata_read",
            headers={"Authorization": f"Basic {self.b64_auth}"}
        )

        if not response_auth.ok:
            raise AcrException(response_auth.text)
        return response_auth.json()["access_token"]

    def has_image_metadata(self, image:str) -> bool:
        """
        Works as an existence check. If the tag for the image
        has the requested tag in the list of available tags
        return True.
        This should work on any docker Registry v2 as it's a standard
        """
        image_name, tag = image.split(":")
        token = self.login(image_name)
        response_metadata = requests.get(
            f"https://{self.url}/v2/{image_name}/tags/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        if not response_metadata.ok:
            raise AcrException(response_metadata.text)
        return tag in response_metadata.json()["tags"]
