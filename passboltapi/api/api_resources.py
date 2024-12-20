# Resources endpoints are used to manage permissions on a Resource.
# 
# https://help.passbolt.com/api/permissions
from typing import Mapping, Optional, List, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from passboltapi import APIClient, PassboltError

import json
import passboltapi.api.api_folders as passbolt_folder_api
import passboltapi.api.api_groups as passbolt_group_api
import passboltapi.api.api_users as passbolt_user_api
import passboltapi.api.api_resources_type as passbolt_resource_type_api

from passboltapi.schema import (
    PassboltValidationError,
    PassboltResourceError,
    PassboltResourceNotFoundError,
    PassboltFolderIdType,
    PassboltResourceIdType,
    PassboltResourceTuple,
    PassboltResourceType,
    PassboltResourceTypeIdType,
    PassboltUserIdType,
    PassboltUserTuple,
    constructor, PassboltSecretTuple, PassboltResourceTypeTuple, PassboltFolderTuple, PassboltGroupTuple,
    PassboltOpenPgpKeyTuple, PassboltPermissionTuple, PassboltGroupIdType,
)

def _encrypt_secrets(api: "APIClient", secret_text: str, recipients: List[PassboltUserTuple]) -> List[Mapping]:
    return [
        {"user_id": user.id, "data": api.encrypt(secret_text, user.gpgkey.fingerprint)} for user in recipients
    ]


def _get_secret(api: "APIClient", resource_id: PassboltResourceIdType) -> PassboltSecretTuple:
    response = api.get(f"/secrets/resource/{resource_id}.json")
    assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
    return PassboltSecretTuple(**response["body"])


def _update_secret(api: "APIClient", resource_id: PassboltResourceIdType, new_secret):
    return api.put(f"/resources/{resource_id}.json", {"secrets": new_secret}, return_response_object=True)


def _json_load_secret(api: "APIClient", secret: PassboltSecretTuple) -> Tuple[str, Optional[str]]:
    try:
        secret_dict = json.loads(api.decrypt(secret.data))
        return secret_dict["password"], secret_dict["description"]
    except (json.decoder.JSONDecodeError, KeyError):
        return api.decrypt(secret.data), None


def _get_secret_type(api: "APIClient", resource_type_id: PassboltResourceTypeIdType) -> PassboltResourceType:
    resource_type: PassboltResourceTypeTuple = passbolt_resource_type_api.get_by_id(
        api=api, resource_type_id=resource_type_id)

    resource_definition = json.loads(resource_type.definition)
    if resource_definition["secret"]["type"] == "string":
        return PassboltResourceType.PASSWORD
    if resource_definition["secret"]["type"] == "object" and set(
            resource_definition["secret"]["properties"].keys()
    ) == {"password", "description"}:
        return PassboltResourceType.PASSWORD_WITH_DESCRIPTION
    raise PassboltError("The resource type definition is not valid or supported yet. ")


def encrypt_resources(api: "APIClient", resources: List[PassboltResourceTuple], user: PassboltUserTuple)\
        -> List[Mapping]:
    """
    Encrypt secrets from a resource list using one user
    """

    return [
        {
            "resource_id": resource.id,
            "user_id": user.id,
            "data": api.encrypt(get_password(api=api, resource_id=resource.id), user.gpgkey.fingerprint)
        }
        for resource in resources
    ]

def get_password_and_description(api: "APIClient", resource_id: PassboltResourceIdType) -> dict:
    resource: PassboltResourceTuple = get_by_id(api=api, resource_id=resource_id)
    secret: PassboltSecretTuple = _get_secret(api=api, resource_id=resource_id)
    secret_type = _get_secret_type(api=api, resource_type_id=resource.resource_type_id)
    if secret_type == PassboltResourceType.PASSWORD:
        return {"password": api.decrypt(secret.data), "description": resource.description}
    elif secret_type == PassboltResourceType.PASSWORD_WITH_DESCRIPTION:
        pwd, desc = _json_load_secret(api=api, secret=secret)
        return {"password": pwd, "description": desc}


def get_password(api: "APIClient", resource_id: PassboltResourceIdType) -> str:
    return get_password_and_description(api=api, resource_id=resource_id)["password"]


def get_description(api: "APIClient", resource_id: PassboltResourceIdType) -> str:
    return get_password_and_description(api=api, resource_id=resource_id)["description"]


def get_shared_resources(api: "APIClient", group: PassboltGroupTuple) -> List[PassboltResourceTuple]:
    """
    Get all resources shared with a specific group
    """
    response = api.get(f"/resources/.json?filter[is-shared-with-group]={group.id}", return_response_object=True)
    response = response.json()["body"]

    return [constructor(PassboltResourceTuple)(resource) for resource in response]

def create(
        api: "APIClient",
        name: str,
        password: str,
        username: str = "",
        description: str = "",
        uri: str = "",
        groups: [str] = None,
        resource_type_id: Optional[PassboltResourceTypeIdType] = None,
        folder_id: Optional[PassboltFolderIdType] = None,
):
    """
    Creates a new resource on passbolt and shares it with the provided folder recipients.
    https://help.passbolt.com/api/resources/create
    """
    if groups is None:
        groups = []
    if not name:
        raise PassboltValidationError(f"Name cannot be None or empty -- {name}!")
    if not password:
        raise PassboltValidationError(f"Password cannot be None or empty -- {password}!")

    r_create = api.post(
        "/resources.json",
        {
            "name": name,
            "username": username,
            "description": description,
            "uri": uri,
            **({"resource_type_id": resource_type_id} if resource_type_id else {}),
            "secrets": [{"data": api.encrypt(password)}],
        },
        return_response_object=True,
    )
    resource = constructor(PassboltResourceTuple)(r_create.json()["body"])

    if folder_id:
        # Get folder
        folder = passbolt_folder_api.get_by_id(api=api, folder_id=folder_id)

        # Move resource
        move_resource_to_folder(api=api, resource_id=resource.id, folder_id=folder_id)

    users_list = []
    groups_list = []

    for group_name in groups:
        try:
            group: PassboltGroupTuple = passbolt_group_api.get_by_name(api=api, group_name=group_name)
            groups_list.append(group)
            users_list.extend(group.groups_users)
        except passbolt_group_api.PassboltGroupNotFoundError:
            pass

    # Update resource data
    resource = get_by_id(api=api, resource_id=resource.id)

    # Convert user list to actual user tuple
    users_list = [passbolt_user_api.get_by_id(api=api, user_id=user["user_id"]) for user in users_list]

    # Share resource
    share_resource_with_users(api=api, resource=resource, password=password, users_list=users_list,
                              groups_list=groups_list)

    return resource


def get_by_id(api: "APIClient", resource_id: PassboltResourceIdType) -> PassboltResourceTuple:
    """
    Read a resource using the resource identifier.

    https://help.passbolt.com/api/resources/read
    """
    response = api.get(f"/resources/{resource_id}.json", return_response_object=True)
    response = response.json()["body"]

    return constructor(PassboltResourceTuple)(response)


def get_by_name(api: "APIClient", name: str,
                folder_parent_id: Optional[PassboltFolderIdType] = None) -> PassboltResourceTuple:
    """
    Read a resource using the resource name. API does not provide search endpoint for resource, so we fetch all
    resources and filter them locally.

    https://help.passbolt.com/api/resources/read-index
    """
    response = api.get(f"/resources.json?")
    resources_array = [constructor(PassboltResourceTuple)(resource) for resource in response["body"]]

    if folder_parent_id:
        resources_filtered = [resource for resource in resources_array if resource.name == name and
                              resource.folder_parent_id == folder_parent_id]
    else:
        resources_filtered = [resource for resource in resources_array if resource.name == name]

    if len(resources_filtered) == 1:
        return resources_filtered[0]
    elif len(resources_filtered) == 0:
        if folder_parent_id:
            raise PassboltResourceNotFoundError(f"No resource found for {name} in folder {folder_parent_id}")
        else:
            raise PassboltResourceNotFoundError(f"No resource found for {name}")
    else:
        if folder_parent_id:
            raise PassboltResourceError(f"More than one resource found for {name} in folder {folder_parent_id}")
        else:
            raise PassboltResourceError(f"More than one resource found for {name}")


def get_permissions_by_id(api: "APIClient", resource_id: PassboltResourceIdType) -> List[PassboltPermissionTuple]:
    """
    Read a resource permissions using the resource identifier.

    https://help.passbolt.com/api/permissions/read
    """
    response = api.get(f"/permissions/resource/{resource_id}.json", return_response_object=True)
    response = response.json()["body"]

    return [constructor(PassboltPermissionTuple)(item) for item in response]

def move_resource_to_folder(api: "APIClient", resource_id: PassboltResourceIdType, folder_id: PassboltFolderIdType):
    """
    Move a resource to the specified folder.

    https://help.passbolt.com/api/resources/move
    """

    r = api.post(
        f"/move/resource/{resource_id}.json", {"folder_parent_id": folder_id}, return_response_object=True
    )
    return r.json()


def update_resource(
        api: "APIClient",
        resource_id: PassboltResourceIdType,
        name: Optional[str] = None,
        username: Optional[str] = None,
        description: Optional[str] = None,
        uri: Optional[str] = None,
        groups: [str] = None,
        resource_type_id: Optional[PassboltResourceTypeIdType] = None,
        password: Optional[str] = None,
):
    """
    Update a resource.

    https://help.passbolt.com/api/resources/update
    """

    # Fetch existing resource
    resource: PassboltResourceTuple = get_by_id(api=api, resource_id=resource_id)

    # Check if groups permissions are set. If not, delete resource and re-create it
    # TODO : improve this logic
    permissions = get_permissions_by_id(api=api, resource_id=resource_id)
    configured_groups=[]

    for permission in permissions:
        if permission.aro == "Group":
            group = passbolt_group_api.get_by_id(api=api, group_id=permission.aro_foreign_key)
            configured_groups.append(group.name)

    # Sort list before comparison
    groups.sort()
    configured_groups.sort()

    if groups != configured_groups:
        delete_by_id(api=api, resource_id=resource_id)
        return create(
            api=api,
            name=name,
            password=password,
            username=username,
            description=description,
            uri=uri,
            groups=groups,
            resource_type_id=resource_type_id,
            folder_id=resource.folder_parent_id
        )

    secret = _get_secret(api=api, resource_id=resource_id)
    secret_type = _get_secret_type(api=api, resource_type_id=resource.resource_type_id)
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

    recipients = passbolt_user_api.list_users(api=api, resource_or_folder_id=resource_id)

    if secret_type == PassboltResourceType.PASSWORD:
        if password is not None:
            assert isinstance(password, str), f"password has to be a string object -- {password}"
            payload["secrets"] = _encrypt_secrets(api=api, secret_text=password, recipients=recipients)
    elif secret_type == PassboltResourceType.PASSWORD_WITH_DESCRIPTION:
        pwd, desc = _json_load_secret(api=api, secret=secret)
        secret_dict = {}
        if description is not None or password is not None:
            secret_dict["description"] = description if description else desc
            secret_dict["password"] = password if password else pwd
        if secret_dict:
            secret_text = json.dumps(secret_dict)
            payload["secrets"] = _encrypt_secrets(api=api, secret_text=secret_text, recipients=recipients)

    if payload:
        r = api.put(f"/resources/{resource_id}.json", payload, return_response_object=True)

    return get_by_id(api=api, resource_id=resource_id)


def share_resource_with_users(
        api: "APIClient",
        resource: PassboltResourceTuple,
        password: str,
        users_list: [PassboltUserTuple],
        groups_list: [PassboltGroupTuple]) -> None:
    """
    Share a resource with a specified list of users
    """

    if len(users_list) == 0:
        return

    lookup_users: Mapping[PassboltUserIdType, PassboltUserTuple] = {user.id: user for user in users_list}
    self_user_id = [user.id for user in users_list if api.user_fingerprint == user.gpgkey.fingerprint]

    if self_user_id:
        self_user_id = self_user_id[0]
    else:
        raise ValueError("User not in passbolt")

    # Cannot share root resource
    if resource.folder_parent_id:
        # Get resource folder
        folder = passbolt_folder_api.get_by_id(api=api, folder_id=resource.folder_parent_id)
    else:
        return

    # Simulate sharing with folder permissions
    permissions = [
        {
            "is_new": True,
            **{k: v for k, v in perm._asdict().items() if k != "id"},
        }
        for perm in folder.permissions if perm.aro == "Group" and
        perm.aro_foreign_key in [group.id for group in groups_list]

        if (perm.aro_foreign_key != self_user_id)
    ]

    if len(permissions) == 0:
        return

    share_payload = {
        "permissions": permissions,
        "secrets": _encrypt_secrets(api=api, secret_text=password, recipients=lookup_users.values()),
    }

    # Simulate sharing with folder perms
    r_simulate = api.post(
        f"/share/simulate/resource/{resource.id}.json", share_payload, return_response_object=True
    )
    r_share = api.put(f"/share/resource/{resource.id}.json", share_payload, return_response_object=True)


def delete_by_id(api: "APIClient", resource_id: PassboltResourceIdType) -> None:
    """
    Delete a resource using its identifier.

    https://help.passbolt.com/api/resources/delete
    """
    api.delete(f"/resources/{resource_id}.json")
