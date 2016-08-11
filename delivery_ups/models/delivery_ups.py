# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import models, fields, _
from openerp.exceptions import ValidationError

from ups_request import UPSRequest, Package


class ProviderUPS(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('ups', "UPS")])

    ups_username = fields.Char(string='UPS Username', groups="base.group_system")
    ups_passwd = fields.Char(string='UPS Password', groups="base.group_system")
    ups_shipper_number = fields.Char(string='UPS Shipper Number', groups="base.group_system")
    ups_access_number = fields.Char(string='UPS AccessLicenseNumber', groups="base.group_system")
    ups_test_mode = fields.Boolean(default=True, string="Test Mode", help="Uncheck this box to use production UPS Web Services")
    ups_default_packaging_type = fields.Selection([('01', 'UPS Letter'),
                                                   ('02', 'Package/customer supplied'),
                                                   ('03', 'UPS Tube'),
                                                   ('04', 'UPS Pak'),
                                                   ('21', 'Express Box'),
                                                   ('24', '25KG Box'),
                                                   ('25', '10KG Box'),
                                                   ('30', 'Pallet'),
                                                   ('2a', 'Small Express Box'),
                                                   ('2b', 'Medium Express Box'),
                                                   ('2c', 'Flat Pack')],
                                                  string="UPS Packaging Type", default='02')
    ups_default_service_type = fields.Selection([('03', 'UPS Ground'),
                                                 ('11', 'UPS Standard'),
                                                 ('01', 'UPS Next Day'),
                                                 ('14', 'UPS Next Day AM'),
                                                 ('13', 'UPS Next Day Air Saver'),
                                                 ('02', 'UPS 2nd Day'),
                                                 ('59', 'UPS 2nd Day AM'),
                                                 ('12', 'UPS 3-day Select'),
                                                 ('65', 'UPS Saver'),
                                                 ('07', 'UPS Worldwide Express'),
                                                 ('08', 'UPS Worldwide Expedited'),
                                                 ('54', 'UPS Worldwide Express Plus'),
                                                 ('96', 'UPS Worldwide Express Freight')],
                                               string="UPS Service Type", default='03')
    ups_package_weight_unit = fields.Selection([('LBS', 'Pounds'), ('KGS', 'Kilograms')], default='LBS')
    ups_package_dimension_unit = fields.Selection([('IN', 'Inches'), ('CM', 'Centimeters')], string="Units for UPS Package Size", default='IN')
    ups_package_height = fields.Integer(string='Package Height', help="Fixed height if not provided on the product packaging.")
    ups_package_width = fields.Integer(string='Package Width', help="Fixed width if not provided on the product packaging.")
    ups_package_length = fields.Integer(string='Package Length', help="Fixed length if not provided on the product packaging.")

    def ups_get_shipping_price_from_so(self, orders):
        res = []
        superself = self.sudo()
        srm = UPSRequest(superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.ups_test_mode)
        ResCurrency = self.env['res.currency']
        for order in orders:
            packages = []
            total_qty = 0
            total_weight = 0
            for line in order.order_line.filtered(lambda line: not line.is_delivery):
                total_qty += line.product_uom_qty
                total_weight += line.product_id.weight * line.product_qty
            packages.append(Package(self, total_weight))

            shipment_info = {
                'total_qty': total_qty  # required when service type = 'UPS Worldwide Express Freight'
            }
            srm.check_required_value(order.company_id.partner_id, order.warehouse_id.partner_id, order.partner_shipping_id, order=order)
            result = srm.get_shipping_price(
                shipment_info=shipment_info, packages=packages, shipper=order.company_id.partner_id, ship_from=order.warehouse_id.partner_id,
                ship_to=order.partner_shipping_id, packaging_type=self.ups_default_packaging_type, service_type=self.ups_default_service_type)

            if result.get('error_message'):
                raise ValidationError(result['error_message'])

            if order.currency_id.name == result['currency_code']:
                price = float(result['price'])
            else:
                quote_currency = ResCurrency.search([('name', '=', result['currency_code'])], limit=1)
                price = quote_currency.compute(float(result['price']), order.currency_id)

            res = res + [price]

        return res

    def ups_send_shipping(self, pickings):
        res = []
        superself = self.sudo()
        srm = UPSRequest(superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.ups_test_mode)
        ResCurrency = self.env['res.currency']
        for picking in pickings:
            packages = []
            total_qty = 0
            if picking.package_ids:
                # Create all packages
                for package in picking.package_ids:
                    total_qty += sum(quant.qty for quant in package.quant_ids)
                    packages.append(Package(self, package.weight, quant_pack=package.packaging_id, name=package.name))

            # Create one package with the rest (the content that is no in a package)
            if picking.weight_bulk:
                packages.append(Package(self, picking.weight_bulk))

            invoice_line_total = 0
            for move in picking.move_lines:
                invoice_line_total += picking.company_id.currency_id.round(move.product_id.lst_price * move.product_qty)

            shipment_info = {
                'description': picking.origin,
                'total_qty': total_qty,
                'ilt_monetary_value': '%d' % invoice_line_total,
                'itl_currency_code': self.env.user.company_id.currency_id.name,
            }
            srm.check_required_value(picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id, picking.partner_id, picking=picking)

            label_file_type = getattr(self, 'x_label_file_type', None) or 'GIF'
            result = srm.send_shipping(
                shipment_info=shipment_info, packages=packages, shipper=picking.company_id.partner_id, ship_from=picking.picking_type_id.warehouse_id.partner_id,
                ship_to=picking.partner_id, packaging_type=self.ups_default_packaging_type, service_type=self.ups_default_service_type, label_file_type=label_file_type)

            if result.get('error_message'):
                raise ValidationError(result['error_message'])

            currency_order = picking.sale_id.currency_id
            if not currency_order:
                currency_order = picking.company_id.currency_id

            if currency_order.name == result['currency_code']:
                price = float(result['price'])
            else:
                quote_currency = ResCurrency.search([('name', '=', result['currency_code'])], limit=1)
                price = quote_currency.compute(float(result['price']), currency_order)

            labels = []
            track_numbers = []
            for track_number, label_binary_data in result.get('label_binary_data').iteritems():
                logmessage = (_("Shipment created into UPS <br/> <b>Tracking Number : </b>%s") % (track_number))
                picking.message_post(body=logmessage)
                if label_file_type == 'GIF':
                    labels.append(('LabelUPS-%s.pdf' % track_number, label_binary_data))
                else:
                    labels.append(('LabelUPS-%s.%s' % (track_number, label_file_type), label_binary_data))
                track_numbers.append(track_number)
            logmessage = (_("Shipping label for packages"))
            picking.message_post(body=logmessage, attachments=labels)

            carrier_tracking_ref = "+".join(track_numbers)

            shipping_data = {
                'exact_price': price,
                'tracking_number': carrier_tracking_ref}
            res = res + [shipping_data]
        return res

    def ups_get_tracking_link(self, pickings):
        res = []
        for picking in pickings:
            res = res + ['http://wwwapps.ups.com/WebTracking/track?track=yes&trackNums=%s' % picking.carrier_tracking_ref]
        return res

    def ups_cancel_shipment(self, picking):
        tracking_ref = picking.carrier_tracking_ref
        if self.ups_test_mode:
            tracking_ref = "1ZISDE016691676846"  # used for testing purpose

        superself = self.sudo()
        srm = UPSRequest(superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.ups_test_mode)
        result = srm.cancel_shipment(tracking_ref)

        if result.get('error_message'):
            raise ValidationError(result['error_message'])
        else:
            picking.message_post(body=_(u'Shipment N° %s has been cancelled' % picking.carrier_tracking_ref))
            picking.write({'carrier_tracking_ref': '',
                           'carrier_price': 0.0})
