# A sample test for passbolt API
#
# This file is used to test various functions of the Passbolt API, used in the ansible modules.
from datetime import datetime

import passboltapi
from passboltapi import PassboltCreateResourceTuple
from passboltapi.schema import PassboltCreateUserTuple

if __name__ == '__main__':
    with passboltapi.PassboltAPI(config_path="config.ini", new_keys=True) as passbolt:

        now = datetime.now()  # current date and time

        new_password = f"passbolt-password@-%s" % (now.strftime("%Y-%m-%d-T%H%M%S"))
        new_resource = PassboltCreateResourceTuple(
            name=new_password,
            password=new_password,
            username="john-doe",
            folder="SECRET-FOLDER",
            groups=["avengers", "my-new-group-because-ca-marche"]
        )
        resource = passbolt.create_or_update_resource(new_resource)

        # Create a user if not exist, create groups if not exist, and add user to groups
        new_user = PassboltCreateUserTuple(
            username="jeanrene.robin@gmail.com",
            first_name="Jean-René",
            last_name="Robin",
            groups=["avengers", "my-new-group-because-ca-marche"]
        )
        user, modified = passbolt.create_or_update_user(new_user)

        # Delete a user
        modified = passbolt.

        # Create a resource if not exist

        # Create a group if not exist

        # Update a group

        # Update a resource

        # Create a resource inside a folder if not exist

        # Update a resource inside a folder
