from base64 import b64encode
import requests
import json
import os
import logging

logger = logging.getLogger('registries_handler')
logger.setLevel(logging.INFO)

# this might be in a config map, so we can handle this dynamically
URLS = {
    "hub.docker.com": {
        "login": {"url": "https://hub.docker.com/v2/users/login/", "auth_type": "json", "token_field": "token"},
        "tags": {"url": "https://hub.docker.com/v2/repositories/%(image)s/tags"}
    },
    "azurecr.io": {
        "login": {"url": "https://%(service)s/oauth2/token?service=%(service)s&scope=repository:%(repo)s:metadata_read", "auth_type": "basic", "token_field": "access_token"},
        "tags": {"url": "https://%(service)s/v2/%(image)s/tags/list"}
    },
    "ghcr.io": {
        "login": {},
        "tags": {"url": "https://api.github.com/orgs/%(organization)s/packages/container/%(image_no_org)s/versions"}
    }
}

class ContainerRegistryClient:
    """
    Class to handle a set of registries actions
    """
    def __init__(self) -> None:
        self.crs = json.load(open(os.getenv('FLASK_APP') + '/registries/registries-list.json'))
        for cr in self.crs.keys():
            self.crs[cr]["login"] = self.needs_auth(cr)
            url_key = self.map_registry_to_url(cr)
            if URLS[url_key]["login"].get("auth_type") == "basic":
                self.crs[cr]["auth"] = b64encode(f"{self.crs[cr]['username']}:{self.crs[cr]['password']}".encode()).decode()
            elif URLS[url_key]["login"].get("auth_type") == "json":
                self.crs[cr]["auth"] = {"username": self.crs[cr]['username'], "password": self.crs[cr]['password']}
            else:
                self.crs[cr]["auth"] = self.crs[cr]["password"]

    def login(self, cr_url:str, cr_cred:str, image:str):
        """
        Get an access token from the CR, works on Azure, should be double checked
        on other services
        """
        url_key = self.map_registry_to_url(cr_url)
        request_args = {
            "url": URLS[url_key]["login"]["url"] % {"service": cr_url, "repo": image}
        }
        if URLS[url_key]["login"]["auth_type"] == "basic":
            request_args["headers"] = {"Authorization": f"Basic {cr_cred}"}
        else:
            request_args["headers"] = {"Content-Type": "application/json"}
            request_args["json"] = cr_cred

        response_auth = requests.get(**request_args)

        if not response_auth.ok:
            return False

        return response_auth.json()[URLS[url_key]["login"]["token_field"]]

    def map_registry_to_url(self, cr):
        """
        """
        return list(filter(lambda x: x in cr, URLS.keys()))[0]

    def needs_auth(self, cr):
        """
        Some services do not need authentication in the form of Basic user:pass base64 token
        """
        url_key = self.map_registry_to_url(cr)
        return URLS[url_key]["login"] != {}

    def parse_image_and_tag(self, image:str):
        """
        Simple string parse, to split the image name from the tag
        if tag doesn't exist, return latest
        """
        if ":" in image:
            return image.split(":")
        return image, "latest"

    def get_url_string_params(self, cr:str, image_name:str):
        return {
            "service": cr,
            "image": image_name,
            "organization": image_name.split("/")[0] if "/" in image_name else image_name,
            "image_no_org": image_name.split("/")[1] if "/" in image_name else image_name
        }

    def find_image_repo(self, image:str) -> bool:
        """
        Works as an existence check. If the tag for the image
        has the requested tag in the list of available tags
        return True.
        This should work on any docker Registry v2 as it's a standard
        """
        image_name, tag = self.parse_image_and_tag(image)
        tags_list = []
        for cr in self.crs.keys():
            if self.crs[cr]["login"]:
                token = self.login(cr, self.crs[cr]['auth'], image_name)
            else:
                token = self.crs[cr]['auth']
            if not token:
                continue

            url_key = self.map_registry_to_url(cr)
            try:
                response_metadata = requests.get(
                    URLS[url_key]["tags"]["url"] % self.get_url_string_params(cr, image_name),
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response_metadata.ok:
                    tags_list = response_metadata.json()
                    break
                else:
                    logger.info(response_metadata.text)
            except ConnectionError as ce:
                logger.info(ce.strerror)

        # Try for open repos?
        if not tags_list:
            return False

        full_image = f"{cr}/{image}"
        if "results" in tags_list:
            return full_image if tag in [t["name"] for t in tags_list["results"]] else False
        elif "tags" not in tags_list:
            return full_image if tag in [t for tags in tags_list for t in tags["metadata"]["container"]["tags"]] else False
        return full_image if tag in tags_list["tags"] else False
