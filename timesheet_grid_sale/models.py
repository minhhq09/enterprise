# -*- coding: utf-8 -*-
from openerp import api, models, fields


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
                    ('validated', '=', True),
                    '&',
                        ('so_line', 'in', self.ids),
                        '|',
                            ('amount', '<=', 0.0),
                            ('project_id', '!=', False)
            ]

        return super(SaleOrderLine, self)._compute_analytic(domain=domain)

class AnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.multi
    def validate(self):
        val = super(AnalyticLine, self).validate()

        # normally this would be done through a computed field, or triggered
        # by the recomputation of self.validated or something, but that does
        # not seem to be an option, and this is apparently the way to force
        # the recomputation of qty_delivered on sale_order_line
        # cf sale.sale_analytic, sale.sale.SaleOrderLine._get_to_invoice_qty

        # look for the so_line of all timesheet lines associated with the
        # same users as the current lines (as they're all implicitly going to
        # be validated by the current validation), then recompute their
        # analytics. Semantically we should roundtrip through employee_ids,
        # but that's an o2m so (lines).mapped('user_id.employee_ids.user_id')
        # should give the same result as (lines).mapped('user_id')
        self.search(['&', ('is_timesheet', '=', True), ('user_id', 'in', self.mapped('user_id').ids)]) \
            .mapped('so_line') \
            .sudo() \
            ._compute_analytic()

        return val

class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all timesheets recorded (approved or not)"),
        ('approved', "Only invoice approved timesheets"),
    ], string="Invoice Timesheets", default=DEFAULT_INVOICED_TIMESHEET)

    @api.multi
    def set_invoiced_timesheet(self):
        self.env['ir.config_parameter'].set_param(
            'sale.invoiced_timesheet',
            self.invoiced_timesheet,
            groups=['base.group_sale_manager']
        )
