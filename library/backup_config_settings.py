#!/usr/bin/python

# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

# debuging portion to display data back to console
# try:
#     from __main__ import display
# except ImportError:
#     from ansible.utils.display import Display
#     display = Display()


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: backup_config_settings
short_description: NetApp ONTAP manage broadcast domains..
version_added: '2.7'
author: NetApp Ansible Team (ng-ansibleteam@netapp.com) (extended by Tom Cummings for Backup Configuration settings)
description:
- Set or Delete a Destination URL, username and password for configuration backup
options:
  state:
    description:
    - Whether the specified settings should exist or not.
    choices: ['present', 'absent']
    default: present
  destination_url:
    description:
    - Specify the backup location url. (only ftp, http and https protocols are supported)
    required: true
  destination_username:
    description:
    - Specify the username used to access the location url
  destination_pass:
    description:
    - Specify the password used to access the location url
TODO:
    split destination url from protocol (enforcing one of the 3 allowed protocols)
    make username/password optional  
    no_log support for supplied password
'''

EXAMPLES = """
    - name: set backup configuration settings
      backup_config_settings:
        state=present
        username={{ netapp_username }}
        password={{ netapp_password }}
        hostname={{ netapp_hostname }}
        destination_url=ftp://backup.org
        desintation_username=backupuser
        destination_pass=password123
    - name: delete backup configuration settings
      backup_config_settings:
        state=absent
        username={{ netapp_username }}
        password={{ netapp_password }}
        hostname={{ netapp_hostname }}
        destination_url=ftp://backup.org
        desintation_username=backupuser
        destination_pass=password123
"""

RETURN = """


"""
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible.module_utils.netapp as netapp_utils

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class ConfigBackupSettings(object):
    """
        Create, Modifies and Destroys a Configuration backup destination url & username/password
    """
    def __init__(self):
        """
            Initialize the ONTAP Configuration backup settings class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            destination_url=dict(required=True, type='str'),
            destination_username=dict(required=True, type='str'),
            destination_pass=dict(required=True, type='str'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        parameters = self.module.params

        # set up state variables
        self.state = parameters['state']
        self.destination_url = parameters['destination_url']
        self.destination_username = parameters['destination_username']
        self.destination_pass = parameters['destination_pass']

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
        return

    def get_config_backup_settings(self):
        """
        Check to see if destination url and username exist on the system
        :return: True/False if current configuration backup destination url and username match supplied values
        :rtype: bool
        """
        config_backup_settings_get = netapp_utils.zapi.NaElement('config-backup-settings-get')
        result = self.server.invoke_successfully(config_backup_settings_get, True)
        
        config_backup_settings_info = result.get_child_by_name('attributes').get_child_by_name('config-backup-settings-type')
        config_backup_exists = None
        # check if job exists, if settings match return True
        if config_backup_settings_info.get_child_content('destination-url') == self.destination_url and \
            config_backup_settings_info.get_child_content('username-for-destination-url') == self.destination_username:
            config_backup_exists = True

        return config_backup_exists

    def set_config_settings(self):
        """
        sets destination url,username and password
        """
        config_obj = netapp_utils.zapi.NaElement('config-backup-settings-modify')
        config_obj.add_new_child("destination-url", self.destination_url)
        config_obj.add_new_child("username-for-destination-url", self.destination_username)

        config_obj_password = netapp_utils.zapi.NaElement('config-backup-settings-password-set')
        config_obj_password.add_new_child("password-for-destination-url", self.destination_pass)

        try:
            self.server.invoke_successfully(config_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error setting configuration settings %s: %s' %
                                  (self.destination_url, to_native(error)),
                                  exception=traceback.format_exc())
        
        try:
            self.server.invoke_successfully(config_obj_password, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error setting configuration password for username %s: %s' %
                                  (self.destination_username, to_native(error)),
                                  exception=traceback.format_exc())

    def delete_config_settings(self):
        """
        Deletes a destination url and username by setting blank strings for all variables
        """
        config_obj_url = netapp_utils.zapi.NaElement('config-backup-settings-modify')
        config_obj_url.add_new_child("destination-url", None)

        config_obj_user = netapp_utils.zapi.NaElement('config-backup-settings-modify')
        config_obj_user.add_new_child("username-for-destination-url", None)
        
        try:
            self.server.invoke_successfully(config_obj_url, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting config destination url settings %s: %s' %
                                  (self.destination_url, to_native(error)),
                                  exception=traceback.format_exc())
        try:
            self.server.invoke_successfully(config_obj_user, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting config username settings %s: %s' %
                                  (self.destination_url, to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        """
        Run Module based on play book
        """
        changed = False
        settings_exist = self.get_config_backup_settings()
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_backup_config", cserver)
        
        if settings_exist:
            if self.state == 'absent':  # delete
                changed = True
            elif self.state == 'present':  # settings exist=True and state is present, no changes. 
                changed = False
        else:
            if self.state == 'present':  # set config settings when settings_exist = None
                changed = True
        if changed:
            if self.module.check_mode:
                pass
            else:
                if self.state == 'present':  # execute set
                    self.set_config_settings()
                elif self.state == 'absent':  # execute delete
                    self.delete_config_settings()
        self.module.exit_json(changed=changed)


def main():
    """
    Creates the NetApp ONTAP Broadcast Domain Object that can be created, deleted and modified.
    """
    obj = ConfigBackupSettings()
    obj.apply()


if __name__ == '__main__':
    main()
