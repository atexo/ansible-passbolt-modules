# Resources type endpoints are used to manage permissions on a Resource.
# 
# https://help.passbolt.com/api/permissions
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from passboltapi import APIClient

from passboltapi.schema import (
    PassboltResourceTypeIdType,
    PassboltResourceTypeTuple,
    constructor,
)


def get_by_id(api: "APIClient", resource_type_id: PassboltResourceTypeIdType) -> PassboltResourceTypeTuple:
    response = api.get(f"/resource-types/{resource_type_id}.json", return_response_object=True)
    response = response.json()["body"]
    return constructor(PassboltResourceTypeTuple)(response)
