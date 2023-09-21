# Users
#
# User are entities with the ability to interact with the application. They are usually represented by one person and 
# have a unique username. The User object returned by the API hence contains the relevant associated fields like 
# Gpgkeys, Roles, profile, avatar, etc.
# 
# https://help.passbolt.com/api/users

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
class PassboltUserNotFoundError(Exception):
    pass


class PassboltUserNotActiveError(Exception):
    pass


# Methods
def describe_user(self, username: str) -> PassboltUserTuple:
    """
    Fetch a single user using its username via the read-index endpoint. First search the user using the username.
    Return a PassboltUserTuple if a user with the exact username provided was found. 
    Throw PassboltUserNotFoundError instead.

    API Reference : https://help.passbolt.com/api/users/read-index
    """
    response = self.get(f"/users.json", params={f"filter[search]": username})
    found_user = [user for user in response["body"] if user["username"] == username]
    
    if len(found_user) == 1:
        return constructor(PassboltUserTuple)(found_user[0])
    else:
        raise PassboltUserNotFoundError(f"User {username} not found")
    
def describe_user_by_id(self, user_id: PassboltUserIdType) -> PassboltUserTuple:
    """
    Fetch a single user using its id.
    Return a PassboltUserTuple if a user was found. Throw PassboltUserNotFoundError instead.

    API Reference : https://help.passbolt.com/api/users/read
    """
    response = self.get(f"/users/{user_id}.json")
    found_user = response["body"]
    
    if found_user:
        return constructor(PassboltUserTuple)(found_user)
    else:
        raise PassboltUserNotFoundError(f"User id {user_id} not found")

def create_user(self, username:str, first_name: str, last_name: str) -> PassboltUserTuple:
    """
    Create a user in Passbolt. Return a PassboltUserTuple if the user was sucessfully created

    API Reference : https://help.passbolt.com/api/users/create
    """

    response = self.post("/users.json", 
                            {
                                "username": username,
                                "profile": {
                                    "first_name": first_name,
                                    "last_name": last_name
                                }
                        }, return_response_object=True)

    response = response.json()
    return constructor(PassboltUserTuple)(response["body"])

def add_user_to_group(self, user_id: PassboltUserIdType, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
    """
    Add user to group. User must be active.
    """

    # Fetch group
    group = self.describe_group_by_id(group_id=group_id)

    # Fetch user
    user = self.describe_user_by_id(user_id = user_id)

    if not user.active:
        raise PassboltUserNotActiveError(f"User {user.username} id {user.id} is inactive : Cannot be added to a grouup")
        
    # Add user in group
    user_list = [{
            "user_id": user.id,
            "is_admin": False
        }]

    group_payload =  { "name": group.name, "groups_users": user_list}

    # Update group in API
    response = self.put(f"/groups/{ group.id }.json", group_payload, return_response_object=True)

    response = response.json()
    return constructor(PassboltGroupTuple)(response["body"])

def remove_user_to_group(self, user_id: PassboltUserIdType, group_id: PassboltGroupIdType) -> PassboltGroupTuple:
    """
    Remove user from group
    """

    # Fetch group
    group = self.describe_group_by_id(group_id=group_id)

    # Fetch user
    user = self.describe_user_by_id(user_id = user_id)

    # Add user in group
    group.groups_users.append(
        {
            "user_id": user.id,
            "delete": True
        }
    )

    # Update group in API
    response = self.put(f"/groups/{ group.id }.json", group, return_response_object=True)

    response = response.json()
    return constructor(PassboltGroupTuple)(response["body"])