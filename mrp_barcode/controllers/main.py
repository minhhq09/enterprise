# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request

from odoo.addons.stock_barcode.controllers.main import StockBarcodeController


class MrpBarcodeController(StockBarcodeController):

    @http.route('/stock_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu(self, barcode, **kw):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action of manufacturing or warning
        """
        picking = super(MrpBarcodeController, self).main_menu(barcode)
        if not picking.get('action') or picking.get('warning'):
            open_manufacturing = self.try_open_manufacturing(barcode)
            if open_manufacturing:
                return open_manufacturing
            return {'warning': _('No picking or manufacturing corresponding to barcode %(barcode)s') % {'barcode': barcode}}
        return picking

    def try_open_manufacturing(self, barcode):
        manufacturing = request.env['mrp.production'].search([
            ('name', '=', barcode),
            ('state', 'in', ('confirmed', 'planned', 'progress'))
        ], limit=1)
        if manufacturing:
            action_manufacturing = request.env.ref('mrp_barcode.mrp_production_form_action_barcode')
            action_manufacturing = action_manufacturing.read()[0]
            action_manufacturing['res_id'] = manufacturing.id
            return {'action': action_manufacturing}
        return False
