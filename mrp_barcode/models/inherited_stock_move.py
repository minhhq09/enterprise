# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _inherit = ['mrp.product.produce', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        product = self.env['product.product'].search([('barcode', '=', barcode)])
        if product == self.product_id:
            self.product_qty += 1
        else:
            lot = self.env['stock.production.lot'].search([('name', '=', barcode), ('product_id', '=', self.product_id.id)])
            if lot and self.product_id.tracking == 'lot':
                if self.lot_id == lot:
                    self.product_qty += 1
                else:
                    self.product_qty = 1
                    self.lot_id = lot.id
            elif lot and self.product_id.tracking == 'serial':
                self.product_qty = 1
                self.lot_id = lot.id
            else:
                move_lots = self.consume_line_ids.filtered(lambda m: m.lot_id.name == barcode)
                if move_lots:
                    move_lots[0].quantity_done += 1
                else:
                    return {'warning': {
                        'title': _('No found'),
                        'message': _('There is no lot for %s barcode') % barcode
                    }}


class StockMoveLots(models.Model):
    _inherit = 'stock.move.lots'

    lot_barcode = fields.Char(related="lot_id.name")


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'barcodes.barcode_events_mixin']

    product_barcode = fields.Char(related='product_id.barcode', string='Barcode')

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        context=dict(self.env.context)
        lot = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', '=', barcode)])
        if context.get('only_create') and context.get('serial'):
            if barcode in self.move_lot_ids.mapped(lambda x: x.lot_id.name):
                return { 'warning': {
                            'title': _('You have entered this serial number already'),
                            'message': _('You have already scanned the serial number "%(barcode)s"') % {'barcode': barcode},
                        }}
            else:
                self.move_lot_ids += self.move_lot_ids.new({'quantity_done': 1.0, 'lot_id': lot.id})
        elif context.get('only_create') and not context.get('serial'):
            move_lots = self.move_lot_ids.filtered(lambda r: r.lot_id.name == barcode)
            if move_lots:
                move_lots[0].quantity_done = move_lots[0].quantity_done + 1.0
            else:
                self.move_lot_ids += self.move_lot_ids.new({'quantity_done': 1.0, 'lot_id': lot.id})
        elif not context.get('only_create'):
            move_lots = self.move_lot_ids.filtered(lambda r: r.lot_id.name == barcode)
            if move_lots:
                if context.get('serial') and move_lots[0].quantity_done == 1.0:
                    return {'warning': {'title': _('You have entered this serial number already'),
                            'message': _('You have already scanned the serial number "%(barcode)s"') % {'barcode': barcode},}}
                else:
                    move_lots[0].quantity_done = move_lots[0].quantity_done + 1.0
                    move_lots[0].plus_visible = (move_lots[0].quantity == 0.0) or (move_lots[0].quantity_done < move_lots[0].quantity)
            else:
                if lot:
                    self.move_lot_ids += self.move_lot_ids.new({'quantity_done': 1.0, 'lot_id': lot.id, 'plus_visible': False})
                else:
                    return { 'warning': {
                        'title': _('No lot found'),
                        'message': _('There is no production lot for "%(product)s" corresponding to "%(barcode)s"') % {'product': self.product_id.name, 'barcode': barcode},
                    }}
