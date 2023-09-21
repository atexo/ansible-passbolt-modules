# Groups
#
# Groups are logical collection of users. They can be used for example to represents departments or projects in an 
# organization. They are especially useful when you want to share Resources with multiple Users at once.
# 
# https://help.passbolt.com/api/groups

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
class PassboltGroupNotFoundError(Exception):
    pass


# Methods
def describe_group(self, group_name: str):
    """
    Fetch a single group using its name via the read-index endpoint. First list all the groups.
    Return a PassboltGroupTuple if a group with the exact name provided was found. 
    Throw PassboltUserNotFoundError instead.
    """
    response = self.get(f"/groups.json")
    found_group = [group for group in response["body"] if group["name"] == group_name]
    
    if len(found_group) == 1:
        return constructor(PassboltGroupTuple)(found_group[0])
    else:
        raise PassboltGroupNotFoundError(f"Group {group_name} not found")
    
def describe_group_by_id(self, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
    """
    Fetch a single group using its id.
    Return a PassboltGroupTuple if the group was found. Throw PassboltUserNotFoundError instead.
    """

    response = self.get(f"/groups/{group_id}.json", params={"contain[groups_users]": 1})
    found_group = response["body"]
    
    if found_group:
        return constructor(PassboltGroupTuple)(found_group)
    else:
        raise PassboltGroupNotFoundError(f"Group id {group_id} not found")

def create_group(self, group_name:str, group_mananger: str) -> PassboltGroupTuple:
    """
    Create a group in Passbolt with a user as group manager.
    Return a PassboltGroupTuple if the group was successfully created.

    API Reference : https://help.passbolt.com/api/groups/create
    """
    manager = self.describe_user(group_mananger)

    response = self.post("/groups.json", 
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
