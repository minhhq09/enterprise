# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    sip_login = fields.Char("SIP Login / Browser's Extension")
    sip_password = fields.Char('SIP Password')
    sip_external_phone = fields.Char("The extension of  your office's phone.")
    sip_always_transfer = fields.Boolean("Always redirect to physical phone", default=False)
    sip_ring_number = fields.Integer("Number of rings",
        default=6, help="The number of rings before cancelling the call")
