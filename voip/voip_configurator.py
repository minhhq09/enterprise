# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp

# add sip_password to the fields that only users who can modify the user (incl. the user herself) see their real contents
from openerp.addons.base.res import res_users
res_users.USER_PRIVATE_FIELDS.append('sip_password')

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
                'ring_number': self.env.user[0].sip_ring_number or 6,
                'mode': self.env['ir.config_parameter'].get_param('crm.voip.mode', default="demo"),
                }

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
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        voip_fields = [
            'sip_login',
            'sip_password',
            'sip_external_phone',
            'sip_always_transfer',
            'sip_ring_number'
        ]
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(voip_fields)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(voip_fields)
        return init_res

    sip_login = fields.Char("SIP Login / Browser's Extension", groups="base.group_user")
    sip_password = fields.Char('SIP Password', groups="base.group_user")
    sip_external_phone = fields.Char("Handset Extension", groups="base.group_user")
    sip_always_transfer = fields.Boolean("Always Redirect to Handset", default=False, groups="base.group_user",
        help="All your outbound calls will be redirected to your handset when the customer accepts your call")
    sip_ring_number = fields.Integer("Number of Rings", default=6, help="The number of rings before the call is defined as refused by the customer.", groups="base.group_user")
