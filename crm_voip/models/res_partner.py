# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.one
    def create_call_in_queue(self, number):
        phonecall = self.env['crm.phonecall'].create({
            'name': 'Call for ' + self.name,
            'duration': 0,
            'user_id': self.env.user.id,
            'partner_id': self.id,
            'state': 'open',
            'partner_phone': number,
            'in_queue': True,
        })
        return phonecall.id
