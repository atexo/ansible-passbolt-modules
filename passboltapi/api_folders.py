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

def read_folder(self, folder_id: PassboltFolderIdType) -> PassboltFolderTuple:
        response = self.get(
            f"/folders/{folder_id}.json", params={"contain[permissions]": True}, return_response_object=True
        )
        response = response.json()
        return constructor(PassboltFolderTuple, subconstructors={"permissions": constructor(PassboltPermissionTuple)})(
            response["body"]
        )

def create_folder(self, name: str, folder_id: PassboltFolderIdType) -> PassboltFolderTuple:
    
    self.read_folder(folder_id=folder_id)

    response = self.post(
        "/folders.json", {"name": name, "folder_parent_id": folder_id}, return_response_object=True
    )

    response = response.json()
    created_folder = constructor(
        PassboltFolderTuple, subconstructors={"permissions": constructor(PassboltPermissionTuple)})(
        response["body"]
    )

    parent_folder = self.read_folder(folder_id)
    
    # get users with access to parent folder
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
        for perm in parent_folder.permissions
        if (perm.aro_foreign_key != self_user_id)
    ]

    share_payload = {
        "permissions": permissions,
    }

    r_share = self.put(f"/share/folder/{created_folder.id}.json", share_payload, return_response_object=True)

    return created_folder

def describe_folder(self, folder_id: PassboltFolderIdType):
    """Shows folder details with permissions that are needed for some downstream task."""
    response = self.get(
        f"/folders/{folder_id}.json",
        params={
            "contain[permissions]": 1,
            "contain[permissions.user.profile]": 1,
            "contain[permissions.group]": 1,
        },
    )
    assert "body" in response.keys(), f"Key 'body' not found in response keys: {response.keys()}"
    assert (
        "permissions" in response["body"].keys()
    ), f"Key 'body.permissions' not found in response: {response['body'].keys()}"
    return constructor(
        PassboltFolderTuple,
        subconstructors={
            "permissions": constructor(PassboltPermissionTuple),
        }
    )(response["body"])
