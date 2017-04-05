# -*- coding: utf-8 -*-

import datetime

from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from taxcloud_request import TaxCloudRequest

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate(self):
        res = True
        if self.fiscal_position_id.is_taxcloud:
            res = self.validate_taxes_on_invoice()
        super(AccountInvoice, self).invoice_validate()
        return res

    @api.multi
    def validate_taxes_on_invoice(self):
        Param = self.env['ir.config_parameter']
        api_id = Param.sudo().get_param('account_taxcloud.taxcloud_api_id')
        api_key = Param.sudo().get_param('account_taxcloud.taxcloud_api_key')
        request = TaxCloudRequest(api_id, api_key)

        shipper = self.company_id or self.env.user.company_id
        request.set_location_origin_detail(shipper)
        request.set_location_destination_detail(self.partner_id)

        request.set_invoice_items_detail(self)

        response = request.get_all_taxes_values()

        if response.get('error_message'):
            raise ValidationError(response['error_message'])

        tax_values = response['values']

        raise_warning = False
        for line in self.invoice_line_ids:
            if not line.price_subtotal:
                tax_rate = 0.0
            else:
                tax_rate = tax_values[line.id] / line.price_subtotal * 100
            if float_compare(line.invoice_line_tax_ids.amount, tax_rate, precision_rounding=4):
                raise_warning = True
                tax = self.env['account.tax'].sudo().search([
                    ('amount', '=', tax_rate),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', 'sale')], limit=1)
                if not tax:
                    tax = self.env['account.tax'].sudo().create({
                        'name': 'Tax %s %%' % (tax_rate),
                        'amount': tax_rate,
                        'amount_type': 'percent',
                        'type_tax_use': 'sale',
                    })
                line.invoice_line_tax_ids = tax

        self._onchange_invoice_line_ids()

        request.client.service.Authorized(
            request.api_login_id,
            request.api_key,
            request.customer_id,
            request.cart_id,
            request.cart_id,
            datetime.datetime.now()
        )

        if raise_warning:
            return {'warning': _('The tax rates have been updated, you may want to check it before validation')}
        else:
            return True
