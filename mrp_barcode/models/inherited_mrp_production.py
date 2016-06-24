# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'barcodes.barcode_events_mixin']

    @api.multi
    def move_for_barcode(self, barcode):
        self.ensure_one()
        product = self.env['product.product'].search([('barcode', '=', barcode)])
        candidates = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('raw_material_production_id', '=', self.id),
            ('state', 'not in', ('done', 'cancel')),
        ]).filtered(lambda x: x.product_id.tracking != 'none')
        return candidates and candidates[0].id or False

