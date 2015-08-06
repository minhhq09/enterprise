# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.tests.common import TransactionCase


class TestDeliveryFedex(TransactionCase):

    def setUp(self):
        # We do not want to overload FedEx with runbot's requests, change this
        # to True in order to test this module
        self.run_tests = False
        # self.run_tests = True

        super(TestDeliveryFedex, self).setUp()

        self.iPod16 = self.env.ref('product.product_product_8')
        self.iMac = self.env.ref('product.product_product_11')

        # Set weight
        self.iPod16.weight = 0.5
        self.iMac.weight = 11

        # Add a full address to "Your Company"
        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({'country_id': self.env.ref('base.us').id,
                                 'state_id': self.env.ref('base.state_us_39').id})
        self.agrolait = self.env.ref('base.res_partner_2')
        self.agrolait.write({'country_id': self.env.ref('base.be').id})
        self.delta_pc = self.env.ref('base.res_partner_4')

    def test_01_fedex_basic_international_flow(self):
        if not self.run_tests:
            return True

        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPod16.id,
                    'name': "[A6678] iPod (16 GB)",
                    'product_uom_qty': 1.0}

        so_vals = {'partner_id': self.agrolait.id,
                   'carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id,
                   'order_policy': 'picking',
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        self.assertGreater(sale_order.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")

        sale_order.action_button_confirm()
        self.assertEquals(len(sale_order.picking_ids), 1, "The Sale Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEquals(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.force_assign()

        picking.do_prepare_partial()
        self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

        picking.do_transfer()

        self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEquals(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_fedex_basic_us_domestic_flow(self):
        if not self.run_tests:
            return True

        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPod16.id,
                    'name': "[A6678] iPod (16 GB)",
                    'product_uom_qty': 1.0}

        so_vals = {'partner_id': self.delta_pc.id,
                   'carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_us').id,
                   'order_policy': 'picking',
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)

        self.assertGreater(sale_order.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")

        sale_order.action_button_confirm()
        self.assertEquals(len(sale_order.picking_ids), 1, "The Sale Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEquals(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.force_assign()

        picking.do_prepare_partial()
        self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

        picking.do_transfer()

        self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEquals(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_fedex_multipackage_international_flow(self):
        if not self.run_tests:
            return True

        SaleOrder = self.env['sale.order']

        sol_1_vals = {'product_id': self.iPod16.id,
                      'name': "[A6678] iPod (16 GB)",
                      'product_uom_qty': 1.0}
        sol_2_vals = {'product_id': self.iMac.id,
                      'name': "[A1090] iMac",
                      'product_uom_qty': 1.0}

        so_vals = {'partner_id': self.agrolait.id,
                   'carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id,
                   'order_policy': 'picking',
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order = SaleOrder.create(so_vals)
        self.assertGreater(sale_order.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")

        sale_order.action_button_confirm()
        self.assertEquals(len(sale_order.picking_ids), 1, "The Sale Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEquals(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.force_assign()
        picking.do_prepare_partial()
        # This is done to mimic the barcode interface
        # We put pack each product separately
        po0 = picking.pack_operation_ids[0].id
        po1 = picking.pack_operation_ids[1].id
        picking.process_product_id_from_ui(picking.id, self.iPod16.id, po0)
        picking.action_pack(operation_filter_ids=[po0])
        picking.process_product_id_from_ui(picking.id, self.iMac.id, po1)
        picking.action_pack(operation_filter_ids=[po1])
        # End
        self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")
        self.assertTrue(all([po.result_package_id is not False for po in picking.pack_operation_ids]), "Some products have not been put in packages")

        picking.do_transfer()

        self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEquals(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    # TODO RIM master: other tests scenarios:
    # - incomplete addresses:
    #   * no country
    #   * no state in US
    #   * accents in address
    # - no weight for rating
    # - no service availability between 2 addresses
    # - incorrect weight
    # - cancel twice or with incorrect tracking
