# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------


class VoipConfigurator(models.Model):
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
