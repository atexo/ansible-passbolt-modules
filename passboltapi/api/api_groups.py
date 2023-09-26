# Groups are logical collection of users. They can be used for example to represents departments or projects in an
# organization. They are especially useful when you want to share Resources with multiple Users at once.
# 
# https://help.passbolt.com/api/groups

# Imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from passboltapi import APIClient

import passboltapi.api.api_users as passbolt_user_api

from passboltapi.schema import (
    PassboltGroupIdType,
    PassboltGroupTuple,
    constructor, PassboltUserTuple,
)


# Exceptions
class PassboltGroupNotFoundError(Exception):
    pass


# Methods
def get_by_id(api: "APIClient", group_id: PassboltGroupIdType) -> PassboltGroupTuple:
    """
    Fetch a single group using its id.
    Return a PassboltGroupTuple if the group was found. Throw PassboltUserNotFoundError instead.
    """

    response = api.get(f"/groups/{group_id}.json", params={"contain[groups_users]": 1})
    found_group = response["body"]

    if found_group:
        return constructor(PassboltGroupTuple)(found_group)
    else:
        raise PassboltGroupNotFoundError(f"Group id {group_id} not found")


def get_by_name(api: "APIClient", group_name: str):
    """
    Fetch a single group using its name via the read-index endpoint. First list all the groups.
    Return a PassboltGroupTuple if a group with the exact name provided was found. 
    Throw PassboltUserNotFoundError instead.
    """
    response = api.get(f"/groups.json", params={"contain[groups_users]": 1})

    found_group = [group for group in response["body"] if group["name"] == group_name]

    if len(found_group) == 1:
        return constructor(PassboltGroupTuple)(found_group[0])
    else:
        raise PassboltGroupNotFoundError(f"Group {group_name} not found")


def create_group(api: "APIClient", group_name: str, group_manager: PassboltUserTuple) -> PassboltGroupTuple:
    """
    Create a group in Passbolt with a user as group manager.
    Return a PassboltGroupTuple if the group was successfully created.

    API Reference : https://help.passbolt.com/api/groups/create
    """
    manager = passbolt_user_api.get_by_id(api=api, user_id=group_manager.id)

    response = api.post("/groups.json",
                         {
                             "name": group_name,
                             "groups_users": [
                                 {
                                     "user_id": manager.id,
                                     "is_admin": True
                                 }
                             ]
                         }, return_response_object=True)

    response = response.json()
    return constructor(PassboltGroupTuple)(response["body"])
