import configparser
import logging
import urllib.parse
from typing import List, Mapping, Optional, Tuple, Union

import gnupg
import requests
import platform

import passboltapi.api.api_folders as passbolt_folder_api
import passboltapi.api.api_groups as passbolt_group_api
import passboltapi.api.api_resources as passbolt_resource_api
import passboltapi.api.api_resources_type as passbolt_resource_type_api
import passboltapi.api.api_users as passbolt_user_api

from passboltapi.schema import (
    PassboltCreateResourceTuple,
    PassboltCreateUserTuple,
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
    PassboltOperationResultTuple,
    PassboltRoleIdType,
    PassboltSecretIdType,
    PassboltSecretTuple,
    PassboltUserIdType,
    PassboltUserTuple,
    constructor,
)

# Passbolt API Functions

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

        if platform.system() == "Darwin":
            self.gpg = gnupg.GPG(gnupghome='/usr/local/bin/')
        else:
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


def is_user_in_group(user: PassboltUserTuple, group: PassboltGroupTuple) -> bool:
    """
    Check whether the user is present inside the group
    """

    for user_in_group in group.groups_users:
        if user_in_group["user_id"] == user.id:
            return True

    return False


class PassboltAPI(APIClient):
    """
    Adding a convenience method for getting resources.
    Design Principle: All passbolt aware public methods must accept or output one of PassboltTupleTypes
    """


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


    def list_users(
            self, resource_or_folder_id: Union[None, PassboltResourceIdType, PassboltFolderIdType] = None,
            force_list=True
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
            sub_constructors={
                "gpgkey": constructor(PassboltOpenPgpKeyTuple),
            },
        )(response)
        if isinstance(users, PassboltUserTuple) and force_list:
            return [users]
        return users


    def import_public_keys(self, trust_level="TRUST_FULLY"):
        # get all users
        users = self.list_users()
        for user in users:
            if user.gpgkey and user.gpgkey.armored_key:
                self.gpg.import_keys(user.gpgkey.armored_key)
                self.gpg.trust_keys(user.gpgkey.fingerprint, trust_level)


    # Folder API

    def create_or_get_folder(self, name: str,
                             folder_parent_id: PassboltFolderIdType = None) -> PassboltOperationResultTuple:
        """
        Create a folder if not exist. Parent folder can be set using the parent folder name.
        """

        result_tuple = PassboltOperationResultTuple(None, False)

        if folder_parent_id:
            parent_folder: PassboltFolderTuple = passbolt_folder_api.get_by_id(api=self, folder_id=folder_parent_id)
            folder_parent_id = parent_folder.id
        else:
            parent_folder = None
            folder_parent_id = None

        try:
            result_tuple.data = passbolt_folder_api.get_by_name(api=self, name=name, folder_parent_id=folder_parent_id)
        except passbolt_folder_api.PassboltFolderNotFoundError:
            print(f"Folder %s not found in folder %s" % (name, folder_parent_id))
            result_tuple.changed = True
            result_tuple.data = passbolt_folder_api.create(api=self, name=name, folder_parent_id=folder_parent_id)

        return result_tuple


    # Group API

    def create_or_get_group(self, group_name: str) -> tuple[PassboltGroupTuple, bool]:
        """
        Create group if not exist
        """
        try:
            return passbolt_group_api.get_by_name(api=self, group_name=group_name), False
        except passbolt_group_api.PassboltGroupNotFoundError:
            group_manager = passbolt_user_api.get_me(api=self)
            return passbolt_group_api.create_group(api=self, group_name=group_name, group_manager=group_manager), True


    # Resource API

    def read_resource_by_name(self, name: str) -> PassboltResourceTuple:
        """
        Read a single resource in Passbolt
        """
        return passbolt_resource_api.get_by_name(api=self, name=name)


    def create_or_update_resource(self, resource: PassboltCreateResourceTuple) -> PassboltOperationResultTuple:
        """
        Create resource if not found in Passbolt. Update it if found.
        """

        result_tuple = PassboltOperationResultTuple(None, False)

        try:
            existing_resource = passbolt_resource_api.get_by_name(api=self,
                                                                  name=resource.name,
                                                                  folder_parent_id=resource.folder_id)

            passbolt_resource_api.move_resource_to_folder(
                api=self, resource_id=existing_resource.id, folder_id=resource.folder_id)

            updated_resource: PassboltResourceTuple = passbolt_resource_api.update_resource(
                api=self,
                resource_id=existing_resource.id,
                groups=resource.groups,
                name=resource.name,
                username=resource.username,
                description=resource.description,
                uri=resource.uri,
                password=resource.password
            )

            # Compare existing and updated resource
            result_tuple.changed = resource.name == updated_resource.name and \
                                   resource.description == updated_resource.description and \
                                   resource.uri == updated_resource.uri

            result_tuple.data = updated_resource

        except passbolt_resource_api.PassboltResourceNotFoundError:

            result_tuple.changed = True

            created_resource = passbolt_resource_api.create(
                api=self,
                name=resource.name,
                username=resource.username,
                description=resource.description,
                uri=resource.uri,
                password=resource.password,
                folder_id=resource.folder_id,
                groups=resource.groups
            )

            result_tuple.data = created_resource

        return result_tuple


    def remove_resource_by_name(self, name: str) -> PassboltOperationResultTuple:
        """
        Remove a single resource
        """

        result_tuple = PassboltOperationResultTuple(name, False)

        try:
            existing_resource = passbolt_resource_api.get_by_name(api=self, name=name)
            passbolt_resource_api.delete_by_id(api=self, resource_id=existing_resource.id)
            result_tuple.changed = True
        except passbolt_resource_api.PassboltResourceNotFoundError:
            result_tuple.changed = False

        return result_tuple


    # User API

    def create_or_update_user(self, user: PassboltCreateUserTuple) -> PassboltOperationResultTuple:
        """
        Create user if not found in Passbolt. Update it if found.
        Note : username = email in Passbolt
        """

        result_tuple = PassboltOperationResultTuple(None, False)

        try:
            original_user = passbolt_user_api.get_by_username(api=self, username=user.username)
            result_tuple.data = passbolt_user_api.update_user(
                api=self,
                user_id=original_user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            result_tuple.changed = original_user.username != user.username \
                                   or original_user.profile["first_name"] != user.first_name \
                                   or original_user.profile["last_name"] != user.last_name

        except passbolt_user_api.PassboltUserNotFoundError:
            result_tuple.data = passbolt_user_api.create_user(
                api=self,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            result_tuple.changed = True

        user_groups = passbolt_group_api.get_by_associated_user(api=self, user_id=result_tuple.data.id)
        group_to_remove = [group for group in user_groups if group.name not in user.groups]

        add_user_to_groups_result = self.add_user_to_groups(user=result_tuple.data, groups=user.groups)
        remove_user_from_groups_result = self.remove_user_from_groups(user=result_tuple.data, groups=group_to_remove)

        result_tuple.data = add_user_to_groups_result.data
        result_tuple.changed = result_tuple.changed or add_user_to_groups_result.changed or remove_user_from_groups_result.changed

        return result_tuple


    def add_user_to_groups(self, user: PassboltUserTuple, groups: [str]) -> PassboltOperationResultTuple:
        """
        Find groups passed in groups array, and assign the user to the found groups.
        """

        print("Add user to groups")

        result_tuple = PassboltOperationResultTuple(user, False)

        groups_array: [PassboltGroupTuple] = [self.create_or_get_group(group_name=group_name) for group_name in groups]

        for group, created in groups_array:
            if not is_user_in_group(user, group):
                try:
                    passbolt_user_api.add_user_to_group(api=self, user_id=user.id, group_id=group.id)
                    result_tuple.changed = True
                except passbolt_user_api.PassboltUserNotActiveError:
                    pass

        # Update user using API
        result_tuple.data = passbolt_user_api.get_by_id(api=self, user_id=user.id)

        return result_tuple


    def remove_user_from_groups(self, user: PassboltUserTuple,
                                groups: List[PassboltGroupTuple]) -> PassboltOperationResultTuple:
        """
        Remove user from the specified groups
        """
        result_tuple = PassboltOperationResultTuple(user, False)

        for group in groups:
            # Fetch all group user
            group = passbolt_group_api.get_by_id(api=self, group_id=group.id)
            for user_in_group in group.groups_users:
                if user.id == user_in_group['user_id']:

                    print("Remove user",user.username, "from group", group.name)

                    payload = {
                        "groups_users": [{
                            "id": user_in_group["id"],
                            "delete": True
                        }]
                    }

                    print(payload)

                    result_tuple.changed = True
                    self.put(f"/groups/{group.id}.json",payload, return_response_object=True)

        return result_tuple


    def delete_user(self, username: str) -> PassboltOperationResultTuple:
        """
        Find and delete a user in Passbolt
        """

        result_tuple = PassboltOperationResultTuple(username, False)

        try:
            user_from_api = passbolt_user_api.get_by_username(api=self, username=username)
            passbolt_user_api.delete_by_id(api=self, user_id=user_from_api.id)
            result_tuple.changed = True

        except passbolt_user_api.PassboltUserNotFoundError:
            result_tuple.changed = False

        return result_tuple
