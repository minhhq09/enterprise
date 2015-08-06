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
        return {'pbx_ip': self.env['ir.config_parameter'].get_param('crm.voip.pbx_ip'),
                'wsServer': self.env['ir.config_parameter'].get_param('crm.voip.wsServer'),
                'login': self.env.user[0].sip_login,
                'password': self.env.user[0].sip_password,
                'external_phone': self.env.user[0].sip_external_phone,
                'always_transfer': self.env.user[0].sip_always_transfer,
                'ring_number': self.env.user[0].sip_ring_number}

    #not deleted yet waiting to be sure about the error management.
    # @api.model
    # def error_config(self):
    #     print(self.env.user[0].groups_id)
    #     action = self.env.ref('base.action_res_users_my')
    #     msg = "Wrong configuration for the call. Verify the user's configuration.\nIf you still have issues, please contact your administrator";
    #     raise openerp.exceptions.RedirectWarning(_(msg), action.id, _('Configure The User Now'))

class res_users(models.Model):
    _inherit = 'res.users'

    def __init__(self, pool, cr):
        init_res = super(res_users, self).__init__(pool, cr)

        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['sip_login', 'sip_password', 'sip_external_phone','sip_always_transfer','sip_ring_number'])
        return init_res

    sip_login = fields.Char("SIP Login / Browser's Extension")
    sip_password = fields.Char('SIP Password')
    sip_external_phone = fields.Char("The extension of  your office's phone.")
    sip_always_transfer = fields.Boolean("Always redirect to physical phone", default=False)
    sip_ring_number = fields.Integer("Number of rings", default=6, help="The number of rings before cancelling the call")
