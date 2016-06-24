# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    @api.multi
    def move_lot_update_qty(self, barcode):
        self.ensure_one()
        if self.product_id.barcode == barcode:
            self.qty_producing += 1
            if self.active_move_lot_ids:
                self.active_move_lot_ids.write({'quantity': self.qty_producing})
            return False
        if self.active_move_lot_ids:
            lot = self.env['stock.production.lot'].search([('name', '=', barcode)])
            active_move_lots = self.active_move_lot_ids.filtered(lambda l: l.product_id.id == lot.product_id.id)
            if active_move_lots:
                filter_move_lots = active_move_lots.filtered(lambda m: not m.lot_id)
                move_lots = active_move_lots.filtered(lambda m: m.lot_id.name == barcode)
                if filter_move_lots:
                    if filter_move_lots[0].product_id.tracking == 'serial' and move_lots:
                        return {'warning': _('You have already scanned the serial number "%(barcode)s"') % {'barcode': barcode}}
                    filter_move_lots[0].lot_id = lot.id
                    filter_move_lots[0].quantity_done += 1
                elif move_lots:
                    if move_lots[0].product_id.tracking == 'serial':
                        return {'warning': _('You have already scanned the serial number "%(barcode)s"') % {'barcode': barcode}}
                    move_lots[0].quantity_done += 1
                else:
                    new_move_lot = active_move_lots[0].copy()
                    new_move_lot.write({'lot_id': lot.id, 'quantity_done': 1})
                    self.active_move_lot_ids += new_move_lot
                return active_move_lots.ids
            return {'warning': _('There is no lot for these product for corresponding barcode %(barcode)s') % {'barcode': barcode}}
