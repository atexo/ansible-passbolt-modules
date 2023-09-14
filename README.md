# ansible-passbolt-modules
Modules to manage resources, users and folders in Passbolt

## Resources
Allows you to create, update, delete, and share your passwords in Passbolt.

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
