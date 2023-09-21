# Folders
#
# ermission endpoints are used to manage permissions on a Resource.
# 
# https://help.passbolt.com/api/permissions

# Imports
from typing import List, Mapping, Optional, Tuple, Union
from passboltapi.schema import (
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

# Exceptions
class PassboltValidationError(Exception):
    pass

# Methods
def read_resource(self, resource_id: PassboltResourceIdType) -> PassboltResourceTuple:
    response = self.get(f"/resources/{resource_id}.json", return_response_object=True)
    response = response.json()["body"]
    return constructor(PassboltResourceTuple)(response)

def read_resource_type(self, resource_type_id: PassboltResourceTypeIdType) -> PassboltResourceTypeTuple:
    response = self.get(f"/resource-types/{resource_type_id}.json", return_response_object=True)
    response = response.json()["body"]
    return constructor(PassboltResourceTypeTuple)(response)

def move_resource_to_folder(self, resource_id: PassboltResourceIdType, folder_id: PassboltFolderIdType):
    r = self.post(
        f"/move/resource/{resource_id}.json", {"folder_parent_id": folder_id}, return_response_object=True
    )
    return r.json()

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
    """Creates a new resource on passbolt and shares it with the provided folder recipients"""
    if not name:
        raise PassboltValidationError(f"Name cannot be None or empty -- {name}!")
    if not password:
        raise PassboltValidationError(f"Password cannot be None or empty -- {password}!")

    r_create = self.post(
        "/resources.json",
        {
            "name": name,
            "username": username,
            "description": description,
            "uri": uri,
            **({"resource_type_id": resource_type_id} if resource_type_id else {}),
            "secrets": [{"data": self.encrypt(password)}],
        },
        return_response_object=True,
    )
    resource = constructor(PassboltResourceTuple)(r_create.json()["body"])
    if folder_id:
        folder = self.read_folder(folder_id)
        # get users with access to folder
        users_list = self.list_users_with_folder_access(folder_id)
        lookup_users: Mapping[PassboltUserIdType, PassboltUserTuple] = {user.id: user for user in users_list}
        self_user_id = [user.id for user in users_list if self.user_fingerprint == user.gpgkey.fingerprint]
        if self_user_id:
            self_user_id = self_user_id[0]
        else:
            raise ValueError("User not in passbolt")
        # simulate sharing with folder perms
        permissions = [
            {
                "is_new": True,
                **{k: v for k, v in perm._asdict().items() if k != "id"},
            }
            for perm in folder.permissions
            if (perm.aro_foreign_key != self_user_id)
        ]
        share_payload = {
            "permissions": permissions,
            "secrets": self._encrypt_secrets(password, lookup_users.values()),
        }
        # simulate sharing with folder perms
        r_simulate = self.post(
            f"/share/simulate/resource/{resource.id}.json", share_payload, return_response_object=True
        )
        r_share = self.put(f"/share/resource/{resource.id}.json", share_payload, return_response_object=True)

        self.move_resource_to_folder(resource_id=resource.id, folder_id=folder_id)
    return resource

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
    resource: PassboltResourceTuple = self.read_resource(resource_id=resource_id)
    secret = self._get_secret(resource_id=resource_id)
    secret_type = self._get_secret_type(resource_type_id=resource.resource_type_id)
    resource_type_id = resource_type_id if resource_type_id else resource.resource_type_id
    payload = {
        "name": name,
        "username": username,
        "description": description,
        "uri": uri,
        "resource_type_id": resource_type_id,
    }
    if name is None:
        payload.pop("name")
    if username is None:
        payload.pop("username")
    if description is None:
        payload.pop("description")
    if uri is None:
        payload.pop("uri")

    recipients = self.list_users(resource_or_folder_id=resource_id)
    if secret_type == PassboltResourceType.PASSWORD:
        if password is not None:
            assert isinstance(password, str), f"password has to be a string object -- {password}"
            payload["secrets"] = self._encrypt_secrets(secret_text=password, recipients=recipients)
    elif secret_type == PassboltResourceType.PASSWORD_WITH_DESCRIPTION:
        pwd, desc = self._json_load_secret(secret=secret)
        secret_dict = {}
        if description is not None or password is not None:
            secret_dict["description"] = description if description else desc
            secret_dict["password"] = password if password else pwd
        if secret_dict:
            secret_text = json.dumps(secret_dict)
            payload["secrets"] = self._encrypt_secrets(secret_text=secret_text, recipients=recipients)

    if payload:
        r = self.put(f"/resources/{resource_id}.json", payload, return_response_object=True)
        return r