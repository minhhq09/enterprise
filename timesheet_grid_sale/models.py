# -*- coding: utf-8 -*-
from odoo import api, models, fields

DEFAULT_INVOICED_TIMESHEET = 'all'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _compute_analytic(self, domain=None):
        invoice_approved_only = \
            'approved' == self.env['ir.config_parameter'].sudo().get_param(
                'sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if invoice_approved_only:
            domain = [
                    '&',
                        ('so_line', 'in', self.ids),
                        '|',
                            ('amount', '<=', 0.0),
                            '&',
                                ('is_timesheet', '=', True),
                                ('validated', '=', True),
            ]

        return super(SaleOrderLine, self)._compute_analytic(domain=domain)

class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all timesheets recorded (approved or not)"),
        ('approved', "Only invoice approved timesheets"),
    ], string="Invoice Timesheets")

    @api.multi
    def set_default_invoiced_timesheet(self):
        for record in self:
            self.env['ir.config_parameter'].set_param(
                'sale.invoiced_timesheet',
                record.invoiced_timesheet
            )
        return True

    @api.model
    def get_default_invoiced_timesheet(self, fields):
        result = self.env['ir.config_parameter'].get_param('sale.invoiced_timesheet') or DEFAULT_INVOICED_TIMESHEET
        return {'invoiced_timesheet': result}
