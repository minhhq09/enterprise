# -*- coding: utf-8 -*-

from openerp import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_transfer(self):
        result = super(StockPicking, self).do_transfer()
        so = self.env['sale.order'].search([('name', '=', self.origin)])
        if so.product_id.product_tmpl_id.ebay_use:
            call_data = {
                'OrderLineItemID': so.client_order_ref,
                'Shipped': True
            }
            if self.carrier_tracking_ref and self.carrier_id:
                call_data['Shipment'] = {
                    'ShipmentTrackingDetails': {
                        'ShipmentTrackingNumber': self.carrier_tracking_ref,
                        'ShippingCarrierUsed': self.carrier_id.name,
                    },
                }
            self.env['product.template'].ebay_execute("CompleteSale", call_data)
        return result
