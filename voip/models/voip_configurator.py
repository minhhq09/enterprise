# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------


class voip_configurator(models.Model):
    _name = 'voip.configurator'

    @api.model
    def get_pbx_config(self):
        return {'pbx_ip': self.env['ir.config_parameter'].get_param('crm.voip.pbx_ip', default='localhost'),
                'wsServer': self.env['ir.config_parameter'].get_param('crm.voip.wsServer', default='ws://localhost'),
                'login': self.env.user[0].sip_login,
                'password': self.env.user[0].sip_password,
                'external_phone': self.env.user[0].sip_external_phone,
                'always_transfer': self.env.user[0].sip_always_transfer,
                'ring_number': self.env.user[0].sip_ring_number,
                'mode': self.env['ir.config_parameter'].get_param('crm.voip.mode', default="demo"),
                }

    #not deleted yet waiting to be sure about the error management.
    # @api.model
    # def error_config(self):
    #     print(self.env.user[0].groups_id)
    #     action = self.env.ref('base.action_res_users_my')
    #     msg = "Wrong configuration for the call. Verify the user's configuration.\nIf you still have issues, please contact your administrator";
    #     raise openerp.exceptions.RedirectWarning(_(msg), action.id, _('Configure The User Now'))
