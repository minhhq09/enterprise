# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_print_temando_manifest(self):
        self.ensure_one()

        if self.carrier_id.delivery_type == 'temando':
            return self.carrier_id.temando_get_manifest(self)[0]
        else:
            return False
