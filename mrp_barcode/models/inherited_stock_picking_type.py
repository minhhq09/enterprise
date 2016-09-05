# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    @api.multi
    def get_action_mrp_production_ready_kanban(self):
        action = self._get_action('mrp_barcode.mrp_production_kanban_mrp_barcode')
        return action
