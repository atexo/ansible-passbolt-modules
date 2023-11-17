# A sample test for passbolt API
#
# This file is used to test various functions of the Passbolt API, used in the ansible modules.
from datetime import datetime
from passboltapi import PassboltCreateResourceTuple
from passboltapi.schema import PassboltCreateUserTuple

import passboltapi
import sys

if __name__ == '__main__':
    with passboltapi.PassboltAPI(config_path="config.ini", new_keys=True) as passbolt:

        passbolt.import_public_keys()  # import user keys to allow secrets encryption

        now = datetime.now()  # current date and time

        # parent_folder_name = "MY-PASSWORD-FOLDER"  # folder must exist and be unique in passbolt.
        #
        # folders_hierarchy = ["ATEXO", "intermediate-level", "intermediate-level"]
        #
        # parent_folder = None
        #
        # for i in range(len(folders_hierarchy)):
        #     print("Create folder " + folders_hierarchy[i])
        #     if i == 0:
        #         result = passbolt.create_or_get_folder(name=folders_hierarchy[i])
        #     else:
        #         result = passbolt.create_or_get_folder(name=folders_hierarchy[i], folder_parent_id=result.data.id)
        #     print(result.data)
        #     print("Changed : " + str(result.changed))
        #
        #     parent_folder = result
        #
        # print("Create a user in 'ops' team if not exist, create groups if not exist, and add user to groups")
        # new_user = PassboltCreateUserTuple(
        #     username="alice@acme.com",
        #     first_name="Alice",
        #     last_name="Doe",
        #     groups=["ops", "all"]
        # )
        # result_1 = passbolt.create_or_update_user(new_user)
        # print("Changed : " + str(result_1.changed))

        print("Create a user 'all' team if not exist, create groups if not exist, and add user to groups")
        new_user = PassboltCreateUserTuple(
            username="mouloud.denfir@atexo.com",
            first_name="Mouloud",
            last_name="DENFIR",
            groups=[
                "exploitation",
                "debug"
            ]
        )
        result_1 = passbolt.create_or_update_user(new_user)

        print("Changed : " + str(result_1.changed))
        print(result_1)

        #
        # print("Create a new secured passbolt for 'ops' team")
        # new_password = f"passbolt-very-secured-password@-%s" % (now.strftime("%Y-%m-%d-T%H%M%S"))
        # new_resource = PassboltCreateResourceTuple(
        #     name=new_password,
        #     password=new_password,
        #     username="john-doe",
        #     folder_id=parent_folder.data.id,
        #     groups=["ops"]
        # )
        # result_3 = passbolt.create_or_update_resource(new_resource)
        # print("Folder : " + str(result_3.data))
        # print("Changed : " + str(result_3.changed))

        # print("Create a new password shared with 'all' team")
        # new_password = f"passbolt-password@-%s" % (now.strftime("%Y-%m-%d-T%H%M%S"))
        # new_resource = PassboltCreateResourceTuple(
        #     name="new_password",
        #     password=new_password,
        #     username="john-doe",
        #     folder_id=parent_folder.data.id,
        #     groups=["exploitation"]
        # )
        # result_4 = passbolt.create_or_update_resource(new_resource)
        # print("Changed : " + str(result_4.changed))
        #
        # print("Ensure user 'john-doe@acme.com' is not present")
        # result_5 = passbolt.delete_user("john-doe@acme.com")
        # print("Changed : " + str(result_5.changed))

        # Create a resource if not exist

        # Create a group if not exist

        # Update a group

        # Update a resource

        # Create a resource inside a folder if not exist

        # Update a resource inside a folder
