# Folders
#
# The API allows you to create, update, delete, and share folders.
# Folders can be either shared or personal. Whether they are personal or shared depends on their permissions. 
# One folder (or resource) can only be in one folder for a given user perspective. However, a folder can be in multiple 
# parent folder if you look at all users as a whole. This is to allow users to re-organize folders shared with them in 
# a way that makes sense to them.
# 
# https://help.passbolt.com/api/folders

# Imports
from typing import Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from passboltapi import APIClient

import passboltapi.api.api_users as passbolt_user_api

from passboltapi.schema import (
    PassboltFolderIdType,
    PassboltFolderTuple,
    PassboltPermissionTuple,
    PassboltUserIdType,
    PassboltUserTuple,
    constructor,
)


# Exceptions
class PassboltFolderNotFoundError(Exception):
    pass


class PassboltFolderError(Exception):
    pass


# Methods
def create(api: "APIClient", name: str, parent_folder_id: PassboltFolderIdType = None) -> PassboltFolderTuple:

    if parent_folder_id:
        response = api.post(
            "/folders.json", {"name": name, "parent_folder_id": parent_folder_id}, return_response_object=True
        )
    else:
        response = api.post(
            "/folders.json", {"name": name}, return_response_object=True
        )

    response = response.json()

    created_folder = constructor(
        PassboltFolderTuple, sub_constructors={"permissions": constructor(PassboltPermissionTuple)})(
        response["body"]
    )

    if parent_folder_id:
        parent_folder = get_by_id(api=api, folder_id=parent_folder_id)

        # get users with access to parent folder
        users_list = passbolt_user_api.list_users_with_folder_access(folder_id=parent_folder_id)

        lookup_users: Mapping[PassboltUserIdType, PassboltUserTuple] = {user.id: user for user in users_list}
        self_user_id = [user.id for user in users_list if api.user_fingerprint == user.gpgkey.fingerprint]
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
            for perm in parent_folder.permissions
            if (perm.aro_foreign_key != self_user_id)
        ]

        share_payload = {
            "permissions": permissions,
        }

        r_share = api.put(f"/share/folder/{created_folder.id}.json", share_payload, return_response_object=True)

    return created_folder


def get_by_id(api: "APIClient", folder_id: PassboltFolderIdType) -> PassboltFolderTuple:
    response = api.get(
        f"/folders/{folder_id}.json", params={"contain[permissions]": True}, return_response_object=True
    )
    res = response.json()
    found_folder = res["body"]

    if found_folder:
        return constructor(PassboltFolderTuple, sub_constructors={"permissions": constructor(PassboltPermissionTuple)})(
            found_folder
        )
    else:
        raise PassboltFolderNotFoundError(f"Folder id {folder_id} not found")


def get_by_name(api: "APIClient", name: str, parent_folder_id: PassboltFolderIdType = None) -> [PassboltFolderTuple]:
    response = api.get(f"/folders.json", params={f"filter[search]": name})

    folders_array = [constructor(PassboltFolderTuple)(resource) for resource in response["body"]]

    if parent_folder_id:
        folders_filtered = [resource for resource in folders_array if resource.name == name and
                            resource.parent_folder_id == parent_folder_id]
    else:
        folders_filtered = [resource for resource in folders_array if resource.name == name and
                            resource.parent_folder_id is None]

    if len(folders_filtered) == 1:
        return folders_filtered[0]
    elif len(folders_filtered) == 0:
        if parent_folder_id:
            raise PassboltFolderNotFoundError(f"No folder found for {name} in folder {parent_folder_id}")
        else:
            raise PassboltFolderNotFoundError(f"No folder found for {name}")
    else:
        if parent_folder_id:
            raise PassboltFolderError(f"More than one folder found for {name} in folder {parent_folder_id}" +
                                      f"Please make sure only one {name} folder exist in folder {parent_folder_id}")
        else:
            raise PassboltFolderError(f"More than one folder found for {name}" +
                                      f"Please make sure only one {name} folder exist")
