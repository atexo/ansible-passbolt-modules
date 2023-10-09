#!/usr/bin/python

# Copyright: (c) 2023, Jean-René Robin <jean-rene.robin@atexo.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: passbolt_user

short_description: Manage Passbolt users

version_added: "1.0.0"

description: Allows you to create, update and delete users in Passbolt.

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
    username:
        description: Email as username for the user
        required: true
        type: str
    first_name:
        description: User's first name
        required: true
        type: str
    last_name:
        description: User's last name
        required: true
        type: str
    groups:
        description: List of groups the user will be linked to. Groups will be created if they not exist.
        required: true
        type: str
    state:
        description: Define the state of the user.
        choices:
          - present
          - absent
        required: false
        default: present

author:
    - Jean-René Robin (@mabihan)
'''

EXAMPLES = r'''
# Create a user
- name: "Create user in Passbolt"
  passbolt_user:
    passbolt_server: "{{ passbolt_server }}"
    passbolt_admin_user_fingerprint: "{{ vault_passbolt_admin_user_fingerprint }}"
    passbolt_admin_user_passphrase: "{{ vault_passbolt_admin_user_passphrase }}"
    passbolt_admin_user_public_key_file: "{{ public_key.path }}"
    passbolt_admin_user_private_key_file: "{{ private_key.path }}"
    username: "alice@acme.com"
    first_name: "Alice"
    last_name: "Doe"
    groups:
      - "ops"
      - "all"
    state: present
  delegate_to: localhost

# Remove a user
- name: "Create user in Passbolt"
  passbolt_user:
    passbolt_server: "{{ passbolt_server }}"
    passbolt_admin_user_fingerprint: "{{ vault_passbolt_admin_user_fingerprint }}"
    passbolt_admin_user_passphrase: "{{ vault_passbolt_admin_user_passphrase }}"
    passbolt_admin_user_public_key_file: "{{ public_key.path }}"
    passbolt_admin_user_private_key_file: "{{ private_key.path }}"
    username: "alice@acme.com"
    state: absent
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
        username=dict(type='str', required=True),
        first_name=dict(type='str', required=True),
        last_name=dict(type='str', required=True),
        groups=dict(type='list', required=False, default=[]),
        state=dict(type='str', required=False, default="present"),
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

        # handle user creation or update
        if module.params['state'] == 'present':

            new_user = PassboltCreateUserTuple(
                username=module.params['username'],
                first_name=module.params['first_name'],
                last_name=module.params['last_name'],
                groups=module.params['groups'],
            )

            passbolt_api_result = passbolt.create_or_update_user(new_user)

        elif module.params['state'] == 'absent':

            passbolt_api_result = passbolt.delete_user(module.params['username'])

    result['changed'] = passbolt_api_result.changed
    result['user_id'] = passbolt_api_result.data.id

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
