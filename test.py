import passboltapi

from datetime import datetime

if __name__ == '__main__':
    parent_folder_id = "5b024c98-211c-487e-86f1-0bf75de3f685"

    with passboltapi.PassboltAPI(config_path="config.ini", new_keys=True) as passbolt:
        now = datetime.now()  # current date and time

        new_user_name = f"passbolt-py-user-%s@atexo.com" % (now.strftime("%Y-%m-%d-T%H%M%S"))
        new_group_name = f"passbolt-py-group-%s" % (now.strftime("%Y-%m-%d-T%H:%M:%S"))
        new_folder_name = f"passbolt-py-folder-%s" % (now.strftime("%Y-%m-%d-T%H:%M:%S"))
        new_resource_name = f"passbolt-py-resource-%s" % (now.strftime("%Y-%m-%d-T%H:%M:%S"))

        new_group = passbolt.create_group(new_group_name, "jean-rene.robin@atexo.com")

        print(f"👏  Created group {new_group.name} with uuid {new_group.id}")

        new_user = passbolt.create_user(
            username=new_user_name,
            first_name="Hello",
            last_name="World from Python API"
        )

        print(f"👥  Created user {new_user.username} with uuid {new_user.id}")

        # User must be active to be added to a group
        # updated_group = passbolt.add_user_to_group(
        #     user_id=new_user.id,
        #     group_id=new_group.id
        # )

        new_folder = passbolt.create_folder(
            name=new_folder_name,
            folder_id=parent_folder_id
        )

        print(f"📂  Created folder {new_folder.name} with uuid {new_folder.id}")

        passbolt.import_public_keys()

        new_resource = passbolt.create_resource(
            name=new_resource_name,
            username='Sample username',
            password='password_test',
            uri='https://www.passbolt_uri.com',
            folder_id=new_folder.id
        )

        print(f"🔐  Created resource {new_resource.name} with uuid {new_resource.id} under {new_folder.name} folder")
