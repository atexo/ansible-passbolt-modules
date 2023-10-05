#!/usr/bin/python

# Copyright: (c) 2023, Jean-René Robin <jean-rene.robin@atexo.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: passbolt_resource

short_description: Manage Passbolt resources

version_added: "1.0.0"

description: Allows you to create, update, delete, and share passwords in Passbolt.

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
        description: Name of the resource
        required: true
        type: str
    username:
        description: Username of the resource
        required: true
        type: str
    password:
        description: Password of the resource
        required: true
        type: 
    uri:
        description: URI of the resource
        required: true
        type: str
    folder_name:
        description: Name of the folder where the resource must be created.
        required: false
        type: str
    state:
        description: Define the state of the resource.
        choices:
          - present
          - absent
        required: false
        default: present

author:
    - Jean-René Robin (@mabihan)
'''

EXAMPLES = r'''
# Create a resource
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# Read a resource
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# Update a resource
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# Delete a resource
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''

from ansible.module_utils.basic import AnsibleModule
import sys
sys.path.append("../library")

import passboltapi
from passboltapi import PassboltCreateResourceTuple

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        passbolt_server=dict(type='str', required=True),
        passbolt_admin_user_fingerprint=dict(type='str', required=True),
        passbolt_admin_user_passphrase=dict(type='str', required=True, no_log=True),
        passbolt_admin_user_public_key_file=dict(type='str', required=True, no_log=True),
        passbolt_admin_user_private_key_file=dict(type='str', required=True, no_log=True),
        name=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        uri=dict(type='str', required=False, default=None),
        folder_name=dict(type='str', required=False, default=None),
        state=dict(type='str', required=True),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        original_message='',
        message=''
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

        # handle resource creation or update
        if module.params['state'] == 'present':

            new_resource = PassboltCreateResourceTuple(
                name=module.params['name'],
                uri=module.params['uri'],
                password=module.params['password'],
                username=module.params['username'],
                folder=module.params['folder'],
                groups=module.params['groups'],
            )

            passbolt_api_result = passbolt.create_or_update_resource(new_resource)

        elif module.params['state'] == 'absent':
            print('Try to get resource in passbolt. Delete it if found.')

    result['changed'] = passbolt_api_result.changed

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
