#!/usr/bin/python

# Copyright: (c) 2023, Jean-René Robin <jean-rene.robin@atexo.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: passbolt_folder

short_description: Manage Passbolt folders

version_added: "1.0.0"

description: Allows you to create folders in passbolt

options:
    passbolt_server:
        description: The passbolt server URL
        required: true
        type: str
    passbolt_admin_user_fingerprint:
        description: Fingerprint of the user used to exchange data with Passbolt.
        required: true
        type: str
    passbolt_admin_user_passphrase:
        description: Passphrase of the user used to exchange data with Passbolt.
        required: true
        type: str
    passbolt_admin_user_public_key_file:
        description: Path to the public key file of the user used to exchange data with Passbolt.
        required: true
        type: str
    passbolt_admin_user_private_key_file:
        description: Path to the private key file of the user used to exchange data with Passbolt.
        required: true
        type: str
    name:
        description: Name of the folder
        required: true
        type: str
    parent_folder_id:
        description: Identifier of the parent folder
        required: true
        type: str

author:
    - Jean-René Robin (@mabihan)
'''

EXAMPLES = r'''
- name: "Create folder in Passbolt at root level"
  passbolt_folder:
    passbolt_server: "{{ passbolt_server }}"
    passbolt_admin_user_fingerprint: "{{ vault_passbolt_admin_user_fingerprint }}"
    passbolt_admin_user_passphrase: "{{ vault_passbolt_admin_user_passphrase }}"
    passbolt_admin_user_public_key_file: "{{ public_key.path }}"
    passbolt_admin_user_private_key_file: "{{ private_key.path }}"
    name: "test-folder"
  delegate_to: localhost

- name: "Create a folder under the 'test-folder'"
  passbolt_folder:
    passbolt_server: "{{ passbolt_server }}"
    passbolt_admin_user_fingerprint: "{{ vault_passbolt_admin_user_fingerprint }}"
    passbolt_admin_user_passphrase: "{{ vault_passbolt_admin_user_passphrase }}"
    passbolt_admin_user_public_key_file: "{{ public_key.path }}"
    passbolt_admin_user_private_key_file: "{{ private_key.path }}"
    name: "sub-folder"
    parent_folder_id: "00112233-4455-6677-8899-aabbccddeeff"
  delegate_to: localhost
'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule
import sys
sys.path.append("../library")

import passboltapi

from passboltapi import PassboltCreateUserTuple

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        passbolt_server=dict(type='str', required=True),
        passbolt_admin_user_fingerprint=dict(type='str', required=True),
        passbolt_admin_user_passphrase=dict(type='str', required=True, no_log=True),
        passbolt_admin_user_public_key_file=dict(type='str', required=True, no_log=True),
        passbolt_admin_user_private_key_file=dict(type='str', required=True, no_log=True),
        name=dict(type='str', required=True),
        parent_folder_id=dict(type='str', required=False, default=None),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # prepare configuration dictionary
    config = {
        "PASSBOLT": {
            "SERVER": module.params['passbolt_server'],
            "USER_FINGERPRINT": module.params['passbolt_admin_user_fingerprint'],
            "PASSPHRASE": module.params['passbolt_admin_user_passphrase'],
            "USER_PUBLIC_KEY_FILE": module.params['passbolt_admin_user_public_key_file'],
            "USER_PRIVATE_KEY_FILE": module.params['passbolt_admin_user_private_key_file'],
        }
    }

    with passboltapi.PassboltAPI(config=config, new_keys=True) as passbolt:
        # initialize users keys
        passbolt.import_public_keys()

        passbolt_api_result = passbolt.create_or_get_folder(name=module.params['name'],
                                                            parent_folder_id=module.params['parent_folder_id'])

    result['changed'] = passbolt_api_result.changed
    result['folder_parent_id'] = passbolt_api_result.data.folder_parent_id
    result['folder_id'] = passbolt_api_result.data.id

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
