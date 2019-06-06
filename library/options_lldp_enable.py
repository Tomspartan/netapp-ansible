#!/usr/bin/python

# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type



ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
module: options_lldp_enable
short_description: NetApp ONTAP manage LLDP settings
version_added: '2.8'
author: NetApp Ansible Team (ng-ansibleteam@netapp.com) (extended by Tom Cummings for LLDP settings June 2019)
description:
- Set options.lldp.enable either on or off for all nodes in cluster
options:
  lldp_enable:
    description:
    - Specify if on or off. (only "on" or "off" are supported)
    required: true
"""

EXAMPLES = """
    - name: set lldp enable to ON
      options_lldp_enable:
        username={{ netapp_username }}
        password={{ netapp_password }}
        hostname={{ netapp_hostname }}
        lldp_enable=on

"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible.module_utils.netapp as netapp_utils

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class OptionsLLDP(object):
    """
        Sets options.lldp.enable to on/off
    """

    def __init__(self):
        """
            Initialize the ONTAP Options LLDP Enable class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(lldp_enable=dict(required=True, choices=['on', 'off'])))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec, supports_check_mode=True
        )

        parameters = self.module.params

        # set up state variables
        self.lldp_enable = parameters["lldp_enable"]

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
        return

    def get_lldp_enable_value(self):
        """
        Check to see options.lldp.enable match the supplied value for lldp_enable
        :return: True/False if current lldp_enable matches supplied value
        :rtype: bool
        """
        lldp_info = netapp_utils.zapi.NaElement("options-get-iter")
        options_attributes = netapp_utils.zapi.NaElement("option-info")
        options_attributes.add_new_child("name","lldp.enable")
        
       # search for values that do not match the desired value
        desired_value = str(self.lldp_enable)
        if desired_value == 'on':
            options_attributes.add_new_child("value","off")
        if desired_value == 'off':
            options_attributes.add_new_child("value","on")
        
        # build the rest of the query
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(options_attributes)
        lldp_info.add_child_elem(query)

        result = self.server.invoke_successfully(lldp_info, True)


        lldp_needs_update = None
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) > 0:
            lldp_needs_update = True

        return lldp_needs_update

    def set_lldp_enable_value(self):
        """
        sets lldp_enable_value
        """
        # build main API call
        lldp_options_modify = netapp_utils.zapi.NaElement("options-modify-iter")
        # create query object
        query = netapp_utils.zapi.NaElement("query")
        options_info = netapp_utils.zapi.NaElement("option-info")
        options_info.add_new_child("name","lldp.enable")
        query.add_child_elem(options_info)
        lldp_options_modify.add_child_elem(query)

        attributes = netapp_utils.zapi.NaElement("attributes")
        options_info_obj = netapp_utils.zapi.NaElement("option-info")
        options_info_obj.add_new_child("name","lldp.enable")
        options_info_obj.add_new_child("value", self.lldp_enable)

        attributes.add_child_elem(options_info_obj)
        lldp_options_modify.add_child_elem(attributes)

        try:
            self.server.invoke_successfully(lldp_options_modify, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(
                msg="Error setting options.lldp.enable %s: %s"
                % (self.lldp_enable, to_native(error)),
                exception=traceback.format_exc(),
            )

    def apply(self):
        """
        Run Module based on play book
        """
        changed = False
        settings_need_changing = self.get_lldp_enable_value()
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("lldp_enable", cserver)

        if settings_need_changing:
            changed = True
        else:
            changed = False
        if changed:
            self.set_lldp_enable_value()
        self.module.exit_json(changed=changed)


def main():
    """
    Creates the NetApp ONTAP Broadcast Domain Object that can be created, deleted and modified.
    """
    obj = OptionsLLDP()
    obj.apply()


if __name__ == "__main__":
    main()
