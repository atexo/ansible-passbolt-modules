# A sample test for passbolt API
#
# This file is used to test various functions of the Passbolt API, used in the ansible modules.
from datetime import datetime
import passboltapi.api
import passboltapi.api.api_folders
import passboltapi.api.api_resources
from passboltapi.schema import PassboltFolderTuple, PassboltResourceTypeTuple

import passboltapi

if __name__ == '__main__':
    with passboltapi.PassboltAPI(config_path="config.ini", new_keys=True) as passbolt:

        passbolt.import_public_keys()   # import user keys to allow secrets encryption
        now = datetime.now()            # current date and time

        folder_tree = ["Inventaire", "sem", "recette", "cd976-sem-rec-01"]
        parent_folder:PassboltFolderTuple = None
        folder:PassboltFolderTuple = None

        for i in range(len(folder_tree)):
            print("Get folder " + folder_tree[i])
            if i == 0:
                parent_folder = passboltapi.api.api_folders.get_by_name(passbolt, folder_tree[i])
            elif i == len(folder_tree) - 1:
                folder = passboltapi.api.api_folders.get_by_name(passbolt, folder_tree[i], parent_folder.id)
            else:
                parent_folder = passboltapi.api.api_folders.get_by_name(passbolt, folder_tree[i], parent_folder.id)

        print("Folder ID : " + folder.id)

        resource_to_remove:PassboltResourceTypeTuple = passboltapi.api.api_resources.get_by_name(passbolt, "Accès organisme de formation", folder.id)

        print("Resource ID : " + resource_to_remove.id)

        passboltapi.api.api_resources.delete_by_id(passbolt, resource_to_remove.id)