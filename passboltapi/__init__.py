import configparser
import json
import logging
import urllib.parse
from typing import List, Mapping, Optional, Tuple, Union

import gnupg
import requests

from passboltapi.schema import (
    AllPassboltTupleTypes,
    PassboltDateTimeType,
    PassboltFavoriteDetailsType,
    PassboltFolderIdType,
    PassboltFolderTuple,
    PassboltGroupIdType,
    PassboltGroupTuple,
    PassboltOpenPgpKeyIdType,
    PassboltOpenPgpKeyTuple,
    PassboltPermissionIdType,
    PassboltPermissionTuple,
    PassboltResourceIdType,
    PassboltResourceTuple,
    PassboltResourceType,
    PassboltResourceTypeIdType,
    PassboltResourceTypeTuple,
    PassboltRoleIdType,
    PassboltSecretIdType,
    PassboltSecretTuple,
    PassboltUserIdType,
    PassboltUserTuple,
    constructor,
)

# Passbolt API Functions
from . import api_authentication as PassboltAuthenticationAPI
from . import api_comments as PassboltCommentsAPI
from . import api_favorites as PassboltFavoritesAPI
from . import api_folders as PassboltFoldersAPI
from . import api_groups as PassboltGroupsAPI
from . import api_permissions as PassboltPermissionsAPI
from . import api_resources as PassboltResourcesAPI
from . import api_secrets as PassboltSecretsAPI
from . import api_users as PassboltUsersAPI

LOGIN_URL = "/auth/login.json"
VERIFY_URL = "/auth/verify.json"

class PassboltError(Exception):
    pass


class APIClient:
    def __init__(
        self,
        config: Optional[str] = None,
        config_path: Optional[str] = None,
        new_keys: bool = False,
        delete_old_keys: bool = False,
    ):
        """
        :param config: Config as a dictionary
        :param config_path: Path to the config file.
        :param delete_old_keys: Set true if old keys need to be deleted
        """
        self.config = config
        if config_path:
            self.config = configparser.ConfigParser()
            self.config.read_file(open(config_path, "r"))
        self.requests_session = requests.Session()

        if not self.config:
            raise ValueError("Missing config. Provide config as dictionary or path to configuration file.")
        if not self.config["PASSBOLT"]["SERVER"]:
            raise ValueError("Missing value for SERVER in config.ini")

        self.server_url = self.config["PASSBOLT"]["SERVER"].rstrip("/")
        self.user_fingerprint = self.config["PASSBOLT"]["USER_FINGERPRINT"].upper().replace(" ", "")

        self.gpg = gnupg.GPG()
        
        if delete_old_keys:
            self._delete_old_keys()
        if new_keys:
            self._import_gpg_keys()
        try:
            self.gpg_fingerprint = [i for i in self.gpg.list_keys() if i["fingerprint"] == self.user_fingerprint][0][
                "fingerprint"
            ]

        except IndexError:
            raise Exception("GPG public key could not be found. Check: gpg --list-keys")

        if self.user_fingerprint not in [i["fingerprint"] for i in self.gpg.list_keys(True)]:
            raise Exception("GPG private key could not be found. Check: gpg --list-secret-keys")
        self._login()

    def __enter__(self):
        return self

    def __del__(self):
        self.close_session()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_session()

    def _delete_old_keys(self):
        for i in self.gpg.list_keys():
            self.gpg.delete_keys(i["fingerprint"], True, passphrase="")
            self.gpg.delete_keys(i["fingerprint"], False)

    def _import_gpg_keys(self):
        if not self.config["PASSBOLT"]["USER_PUBLIC_KEY_FILE"]:
            raise ValueError("Missing value for USER_PUBLIC_KEY_FILE in config.ini")
        if not self.config["PASSBOLT"]["USER_PRIVATE_KEY_FILE"]:
            raise ValueError("Missing value for USER_PRIVATE_KEY_FILE in config.ini")
        self.gpg.import_keys(open(self.config["PASSBOLT"]["USER_PUBLIC_KEY_FILE"], "r").read())
        self.gpg.import_keys(open(self.config["PASSBOLT"]["USER_PRIVATE_KEY_FILE"], "r").read())

    def _login(self):
        r = self.requests_session.post(self.server_url + LOGIN_URL, json={"gpg_auth": {"keyid": self.gpg_fingerprint}})
        encrypted_token = r.headers["X-GPGAuth-User-Auth-Token"]
        encrypted_token = urllib.parse.unquote(encrypted_token)
        encrypted_token = encrypted_token.replace("\+", " ")
        token = self.decrypt(encrypted_token)
        self.requests_session.post(
            self.server_url + LOGIN_URL,
            json={
                "gpg_auth": {"keyid": self.gpg_fingerprint, "user_token_result": token},
            },
        )
        self._get_csrf_token()

    def _get_csrf_token(self):
        self.get("/users/me.json", return_response_object=True)  # Fetches the X-CSRF-Token header for future requests

    def encrypt(self, text, recipients=None):
        return str(self.gpg.encrypt(data=text, recipients=recipients or self.gpg_fingerprint, always_trust=True))

    def decrypt(self, text):
        return str(self.gpg.decrypt(text, always_trust=True, passphrase=str(self.config["PASSBOLT"]["PASSPHRASE"])))

    def get_headers(self):
        return {
            "X-CSRF-Token": self.requests_session.cookies["csrfToken"]
            if "csrfToken" in self.requests_session.cookies
            else ""
        }

    def get_server_public_key(self):
        r = self.requests_session.get(self.server_url + VERIFY_URL)
        return r.json()["body"]["fingerprint"], r.json()["body"]["keydata"]

    def delete(self, url):
        r = self.requests_session.delete(self.server_url + url, headers=self.get_headers())
        try:
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            logging.error(r.text)
            raise e

    def get(self, url, return_response_object=False, **kwargs):
        r = self.requests_session.get(self.server_url + url, headers=self.get_headers(), **kwargs)
        try:
            r.raise_for_status()
            if return_response_object:
                return r
            return r.json()
        except requests.exceptions.HTTPError as e:
            logging.error(r.text)
            raise e

    def put(self, url, data, return_response_object=False, **kwargs):
        r = self.requests_session.put(self.server_url + url, json=data, headers=self.get_headers(), **kwargs)
        try:
            r.raise_for_status()
            if return_response_object:
                return r
            return r.json()
        except requests.exceptions.HTTPError as e:
            logging.error(r.text)
            raise e

    def post(self, url, data, return_response_object=False, **kwargs):
        r = self.requests_session.post(self.server_url + url, json=data, headers=self.get_headers(), **kwargs)
        try:
            r.raise_for_status()
            if return_response_object:
                return r
            return r.json()
        except requests.exceptions.HTTPError as e:
            logging.error(r.text)
            raise e

    def close_session(self):
        self.requests_session.close()


class PassboltAPI(APIClient):
    """Adding a convenience method for getting resources.

    Design Principle: All passbolt aware public methods must accept or output one of PassboltTupleTypes"""

    def _json_load_secret(self, secret: PassboltSecretTuple) -> Tuple[str, Optional[str]]:
        try:
            secret_dict = json.loads(self.decrypt(secret.data))
            return secret_dict["password"], secret_dict["description"]
        except (json.decoder.JSONDecodeError, KeyError):
            return self.decrypt(secret.data), None

    def _encrypt_secrets(self, secret_text: str, recipients: List[PassboltUserTuple]) -> List[Mapping]:
        return [
            {"user_id": user.id, "data": self.encrypt(secret_text, user.gpgkey.fingerprint)} for user in recipients
        ]

    def _get_secret(self, resource_id: PassboltResourceIdType) -> PassboltSecretTuple:
        response = self.get(f"/secrets/resource/{resource_id}.json")
        assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
        return PassboltSecretTuple(**response["body"])

    def _update_secret(self, resource_id: PassboltResourceIdType, new_secret):
        return self.put(f"/resources/{resource_id}.json", {"secrets": new_secret}, return_response_object=True)

    def _get_secret_type(self, resource_type_id: PassboltResourceTypeIdType) -> PassboltResourceType:
        resource_type: PassboltResourceTypeTuple = self.read_resource_type(resource_type_id=resource_type_id)
        resource_definition = json.loads(resource_type.definition)
        if resource_definition["secret"]["type"] == "string":
            return PassboltResourceType.PASSWORD
        if resource_definition["secret"]["type"] == "object" and set(
            resource_definition["secret"]["properties"].keys()
        ) == {"password", "description"}:
            return PassboltResourceType.PASSWORD_WITH_DESCRIPTION
        raise PassboltError("The resource type definition is not valid or supported yet. ")

    def get_password_and_description(self, resource_id: PassboltResourceIdType) -> dict:
        resource: PassboltResourceTuple = self.read_resource(resource_id=resource_id)
        secret: PassboltSecretTuple = self._get_secret(resource_id=resource_id)
        secret_type = self._get_secret_type(resource_type_id=resource.resource_type_id)
        if secret_type == PassboltResourceType.PASSWORD:
            return {"password": self.decrypt(secret.data), "description": resource.description}
        elif secret_type == PassboltResourceType.PASSWORD_WITH_DESCRIPTION:
            pwd, desc = self._json_load_secret(secret=secret)
            return {"password": pwd, "description": desc}

    def get_password(self, resource_id: PassboltResourceIdType) -> str:
        return self.get_password_and_description(resource_id=resource_id)["password"]

    def get_description(self, resource_id: PassboltResourceIdType) -> str:
        return self.get_password_and_description(resource_id=resource_id)["description"]

    def iterate_resources(self, params: Optional[dict] = None):
        params = params or {}
        url_params = urllib.parse.urlencode(params)
        if url_params:
            url_params = "?" + url_params
        response = self.get("/resources.json" + url_params)
        assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
        resources = response["body"]
        for resource in resources:
            yield resource

    def list_resources(self, folder_id: Optional[PassboltFolderIdType] = None):
        params = {
            **({"filter[has-id][]": folder_id} if folder_id else {}),
            "contain[children_resources]": True,
        }
        url_params = urllib.parse.urlencode(params)
        if url_params:
            url_params = "?" + url_params
        response = self.get("/folders.json" + url_params)
        assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
        response = response["body"][0]
        assert "children_resources" in response.keys(), (
            f"Key 'body[].children_resources' not found in response " f"keys: {response.keys()} "
        )
        return constructor(PassboltResourceTuple)(response["children_resources"])

    def list_users_with_folder_access(self, folder_id: PassboltFolderIdType) -> List[PassboltUserTuple]:
        folder_tuple = self.describe_folder(folder_id)
        # resolve users
        user_ids = set()
        # resolve users from groups
        for perm in folder_tuple.permissions:
            if perm.aro == "Group":
                group_tuple: PassboltGroupTuple = self.describe_group_by_id(perm.aro_foreign_key)
                for group_user in group_tuple.groups_users:
                    user_ids.add(group_user["user_id"])
            elif perm.aro == "User":
                user_ids.add(perm.aro_foreign_key)
        return [user for user in self.list_users() if user.id in user_ids]

    def list_users(
        self, resource_or_folder_id: Union[None, PassboltResourceIdType, PassboltFolderIdType] = None, force_list=True
    ) -> List[PassboltUserTuple]:
        if resource_or_folder_id is None:
            params = {}
        else:
            params = {"filter[has-access]": resource_or_folder_id, "contain[user]": 1}
        params["contain[permission]"] = True
        response = self.get(f"/users.json", params=params)
        assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
        response = response["body"]
        users = constructor(
            PassboltUserTuple,
            subconstructors={
                "gpgkey": constructor(PassboltOpenPgpKeyTuple),
            },
        )(response)
        if isinstance(users, PassboltUserTuple) and force_list:
            return [users]
        return users

    def import_public_keys(self, trustlevel="TRUST_FULLY"):
        # get all users
        users = self.list_users()
        for user in users:
            if user.gpgkey and user.gpgkey.armored_key:
                self.gpg.import_keys(user.gpgkey.armored_key)
                self.gpg.trust_keys(user.gpgkey.fingerprint, trustlevel)

    # Group API
    def describe_group(self, group_name: str):
        return PassboltGroupsAPI.describe_group(self, group_name)
        
    def describe_group_by_id(self, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
        return PassboltGroupsAPI.describe_group_by_id(self, group_id)
    
    def create_group(self, group_name:str, group_mananger: str) -> PassboltGroupTuple:
        return PassboltGroupsAPI.create_group(self, group_name, group_mananger)

    # Folder API
    def read_folder(self, folder_id: PassboltFolderIdType) -> PassboltFolderTuple:
        return PassboltFoldersAPI.read_folder(self, folder_id)

    def create_folder(self, name: str, folder_id: PassboltFolderIdType) -> PassboltFolderTuple:
        return PassboltFoldersAPI.create_folder(self, name, folder_id)

    def describe_folder(self, folder_id: PassboltFolderIdType):
        return PassboltFoldersAPI.describe_folder(self, folder_id)

    # Resource API
    def read_resource(self, resource_id: PassboltResourceIdType) -> PassboltResourceTuple:
        return PassboltResourcesAPI.read_resource(self, resource_id)

    def read_resource_type(self, resource_type_id: PassboltResourceTypeIdType) -> PassboltResourceTypeTuple:
        return PassboltResourcesAPI.read_resource_type(self, resource_type_id)
    
    def move_resource_to_folder(self, resource_id: PassboltResourceIdType, folder_id: PassboltFolderIdType):
        return PassboltResourcesAPI.move_resource_to_folder(self, resource_id, folder_id)

    def create_resource(
        self,
        name: str,
        password: str,
        username: str = "",
        description: str = "",
        uri: str = "",
        resource_type_id: Optional[PassboltResourceTypeIdType] = None,
        folder_id: Optional[PassboltFolderIdType] = None,
    ):
        return PassboltResourcesAPI.create_resource(self, name, password, username, description, uri, 
                                                          resource_type_id, folder_id)

    def update_resource(
        self,
        resource_id: PassboltResourceIdType,
        name: Optional[str] = None,
        username: Optional[str] = None,
        description: Optional[str] = None,
        uri: Optional[str] = None,
        resource_type_id: Optional[PassboltResourceTypeIdType] = None,
        password: Optional[str] = None,
    ):
        return PassboltResourcesAPI.update_resource(self, resource_id, name, password, username, description, uri, 
                                                          resource_type_id, password)

    # User API
    def describe_user(self, username: str) -> PassboltUserTuple:
        return PassboltUsersAPI.describe_user(self, username)
        
    def describe_user_by_id(self, user_id: PassboltUserIdType) -> PassboltUserTuple:
        return PassboltUsersAPI.describe_user_by_id(self, user_id)

    def create_user(self, username:str, first_name: str, last_name: str) -> PassboltUserTuple:
        return PassboltUsersAPI.create_user(self, username, first_name, last_name)

    def add_user_to_group(self, user_id: PassboltUserIdType, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
        return PassboltUsersAPI.add_user_to_group(self, user_id, group_id)
    
    def remove_user_to_group(self, user_id: PassboltUserIdType, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
        return PassboltUsersAPI.remove_user_to_group(self, user_id, group_id)