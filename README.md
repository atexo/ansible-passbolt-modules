# ansible-passbolt-modules
Modules to manage resources, users and folders in Passbolt

## Requirements
- gnupg

## Installation
1. Copy the `passboltapi` folder into the `library` folder of ansible
2. Copy the `passbolt_folder.py`, `passbolt_resource.py` and `passbolt_user.py` files into the `plugins/modules` folder.
Note : We're using https://gilt.readthedocs.io/en/latest/ for this purpose.

## Example inventory 
```yaml
---
passbolt_server: "https://passbolt.example.com"

passbolt_admin_user_fingerprint: "W4BeH9tZ5nTVgb7sxkr2MDYpRAhXGCFE"
passbolt_admin_user_passphrase: "kGvrJsd6eSCjN4tHb5MAKRZ3Wcx7UL28"
passbolt_admin_user_private_key: |
  -----BEGIN PGP PRIVATE KEY BLOCK-----

  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGT
  -----END PGP PRIVATE KEY BLOCK-----

passbolt_admin_user_public_key: |
  -----BEGIN PGP PUBLIC KEY BLOCK-----

  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGTxlWkBDACUYV0V6SES4cvsPluIEBrmlSkiy9VCSb0YfbyRteNMaVdQ
  xcTGBGT
  -----END PGP PUBLIC KEY BLOCK-----
...
```

## Folders
Allows you to create folders.
**Note : This API implementation does not allow two folders to have the same name in Passbolt.**

```yaml
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
    parent_folder_name: "test-folder"
  delegate_to: localhost
```

## Resources
Allows you to create, update, delete, and share your passwords.

```yaml
name: "Create resource in Passbolt"
passbolt_resources:
    passbolt_server: https://passbolt.example.com
    passbolt_admin_user_fingerprint: 66890FKF4DAA4D94FKD842JGI618931835467EDC71FFA
    passbolt_admin_user_passphrase: adminsecuredpassword
    passbolt_admin_user_public_key_file: passbolt_public.txt
    passbolt_admin_user_private_key_file: passbolt_private.txt
    name: my-api-password
    content: the-actual-password
    folder_id: 5b024c98-777e-487e-99f1-0bf75de3f685
    state: present
```

## Users
Allow you to create and delete users

```yaml
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
```