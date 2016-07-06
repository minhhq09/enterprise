# -*- coding: utf-8 -*-

from odoo import models, api


class res_partner(models.Model):
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
