# Permission
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