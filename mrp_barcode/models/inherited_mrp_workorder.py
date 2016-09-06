# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        if self.product_id.barcode == barcode:
            self.qty_producing += 1
        elif self.active_move_lot_ids or self.product_id.tracking != 'none':
            lot = self.env['stock.production.lot'].search([('name', '=', barcode)], limit=1)
            if lot.product_id == self.product_id:
                self.final_lot_id  = lot
            else:
                active_move_lots = self.active_move_lot_ids.filtered(lambda l: l.product_id == lot.product_id)
                if active_move_lots:
                    blank_move_lot = active_move_lots.filtered(lambda m: not m.lot_id)
                    move_lots = active_move_lots.filtered(lambda m: m.lot_id.name == barcode)
                    if move_lots:
                        move_lots[0].quantity_done += 1.0 # Problem is it will immediately consume more than foreseen on the second scan (check if it becomes red)
                    elif blank_move_lot:
                        blank_move_lot[0].lot_id = lot.id
