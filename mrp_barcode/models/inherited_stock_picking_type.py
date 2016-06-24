# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    @api.multi
    def get_action_picking_tree_ready_kanban(self):
        if self.code == 'mrp_operation':
            return self._get_action('mrp_barcode.mrp_production_kanban_mrp_barcode')
        return super(StockPickingType, self).get_action_picking_tree_ready_kanban()
