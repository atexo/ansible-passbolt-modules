# User are entities with the ability to interact with the application. They are usually represented by one person and
# have a unique username. The User object returned by the API hence contains the relevant associated fields like 
# Gpgkeys, Roles, profile, avatar, etc.
# 
# https://help.passbolt.com/api/users

# Imports
from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from passboltapi import APIClient

import passboltapi.api.api_groups as passbolt_group_api
import passboltapi.api.api_folders as passbolt_folder_api

from passboltapi.schema import (
    PassboltFolderIdType,
    PassboltGroupIdType,
    PassboltGroupTuple,
    PassboltResourceIdType,
    PassboltUserIdType,
    PassboltUserTuple,
    constructor, PassboltOpenPgpKeyTuple,
)


# Exceptions
class PassboltUserNotFoundError(Exception):
    pass


class PassboltUserNotActiveError(Exception):
    pass


# Create methods
def create_user(api: "APIClient", username: str, first_name: str, last_name: str) -> PassboltUserTuple:
    """
    Create a user in Passbolt. Return a PassboltUserTuple if the user was successfully created

    API Reference : https://help.passbolt.com/api/users/create
    """

    response = api.post("/users.json",
                         {
                             "username": username,
                             "profile": {
                                 "first_name": first_name,
                                 "last_name": last_name
                             }
                         }, return_response_object=True)

    response = response.json()
    return constructor(PassboltUserTuple)(response["body"])


# Read methods
def get_me(api: "APIClient") -> PassboltUserTuple:
    """
    Fetch current logged-in user
    https://help.passbolt.com/api/users/read
    """
    response = api.get(f"/users/me.json")
    found_user = response["body"]

    if found_user:
        return constructor(PassboltUserTuple)(found_user)
    else:
        raise PassboltUserNotFoundError(f"Current user not found")


def get_by_id(api: "APIClient", user_id: PassboltUserIdType) -> PassboltUserTuple:
    """
    Fetch a single user using its id.
    Return a PassboltUserTuple if a user was found. Throw PassboltUserNotFoundError instead.

    API Reference : https://help.passbolt.com/api/users/read
    """
    response = api.get(f"/users/{user_id}.json")
    found_user = response["body"]

    if found_user:
        return constructor(PassboltUserTuple)(found_user)
    else:
        raise PassboltUserNotFoundError(f"User id {user_id} not found")


def get_by_username(api: "APIClient", username: str) -> PassboltUserTuple:
    """
    Fetch a single user using its username via the read-index endpoint. First search the user using the username.
    Return a PassboltUserTuple if a user with the exact username provided was found.
    Throw PassboltUserNotFoundError instead.

    API Reference : https://help.passbolt.com/api/users/read-index
    """
    response = api.get(f"/users.json", params={f"filter[search]": username})
    found_user = [user for user in response["body"] if user["username"] == username]

    if len(found_user) == 1:
        return constructor(PassboltUserTuple)(found_user[0])
    else:
        raise PassboltUserNotFoundError(f"User {username} not found")


def list_users(
    api: "APIClient", resource_or_folder_id: Union[None, PassboltResourceIdType, PassboltFolderIdType] = None, force_list=True
) -> List[PassboltUserTuple]:
    if resource_or_folder_id is None:
        params = {}
    else:
        params = {"filter[has-access]": resource_or_folder_id, "contain[user]": 1}
    params["contain[permission]"] = True
    response = api.get(f"/users.json", params=params)
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


def list_users_with_folder_access(api: "APIClient", folder_id: PassboltFolderIdType) -> List[PassboltUserTuple]:
    folder_tuple = passbolt_folder_api.get_by_id(api=api, folder_id=folder_id)
    # resolve users
    user_ids = set()
    # resolve users from groups
    for perm in folder_tuple.permissions:
        if perm.aro == "Group":
            group_tuple: PassboltGroupTuple = passbolt_group_api.get_by_id(api=api, group_id=perm.aro_foreign_key)
            for group_user in group_tuple.groups_users:
                user_ids.add(group_user["user_id"])
        elif perm.aro == "User":
            user_ids.add(perm.aro_foreign_key)
    return [user for user in list_users(api=api) if user.id in user_ids]


# Update methods


def add_user_to_group(api: "APIClient", user_id: PassboltUserIdType, group_id: PassboltGroupIdType)\
        -> PassboltGroupTuple:
    """
    Add user to group. User must be active.
    """

    # Fetch group
    group = passbolt_group_api.get_by_id(api=api, group_id=group_id)

    # Fetch user
    user = get_by_id(api=api, user_id=user_id)

    if not user.active:
        raise PassboltUserNotActiveError(f"User {user.username} id {user.id} is inactive : Cannot be added to a grouup")

    # Add user in group
    user_list = [{
        "user_id": user.id,
        "is_admin": False
    }]

    group_payload = {"name": group.name, "groups_users": user_list}

    # Update group in API
    response = api.put(f"/groups/{group.id}.json", group_payload, return_response_object=True)

    response = response.json()
    return constructor(PassboltGroupTuple)(response["body"])


def remove_user_to_group(api: "APIClient", user_id: PassboltUserIdType, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
    """
    Remove user from group
    """

    # Fetch group
    group = passbolt_group_api.get_by_id(api=api, group_id=group_id)

    # Fetch user
    user = get_by_id(api=api, user_id=user_id)

    # Add user in group
    group.groups_users.append(
        {
            "user_id": user.id,
            "delete": True
        }
    )

    # Update group in API
    response = api.put(f"/groups/{group.id}.json", group, return_response_object=True)

    response = response.json()
    return constructor(PassboltGroupTuple)(response["body"])


# Delete methods
def delete_by_id(api: "APIClient", user_id: PassboltResourceIdType):
    """
    Delete a user using its identifier.

    https://help.passbolt.com/api/users/delete
    """
    api.delete(f"/users/{user_id}.json")
