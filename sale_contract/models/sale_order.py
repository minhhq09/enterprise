# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
import datetime

from openerp import api, fields, models
from openerp.tools.translate import _


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    def _get_subscription(self):
        for order in self:
            order.subscription_id = self.env['sale.subscription'].search([('analytic_account_id', '=', order.project_id.id)], limit=1)

    def _search_subscription(self, operator, value):
        if operator not in ['=', '!=', 'in', 'not in']:
            return []
        an_accounts = self.env['sale.subscription'].read_group([('id', operator, value)], ['analytic_account_id'], ['analytic_account_id'])
        aa_ids = [aa['analytic_account_id'][0] for aa in an_accounts]

        return [('project_id', operator, aa_ids)]

    subscription_management = fields.Selection(string='Subscription Management', selection=[('create', 'Creation'), ('renew', 'Renewal'), ('upsell', 'Upselling')],
                                      help="Creation: The Sales Order created the subscription\n"
                                            "Upselling: The Sales Order added lines to the subscription\n"
                                            "Renewal: The Sales Order replaced the subscription's content with its own")
    subscription_id = fields.Many2one('sale.subscription', 'Subscription', compute=_get_subscription, search=_search_subscription)

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.subscription_id:
                # no need for updates if the contract was juste created
                if not self.env.context.get('create_contract'):
                    # wipe the subscription clean if needed
                    if order.subscription_management == 'renew':
                        to_remove = [(2, line.id, 0) for line in order.subscription_id.recurring_invoice_line_ids]
                        order.subscription_id.sudo().write({'recurring_invoice_line_ids': to_remove, 'description': order.note, 'state': 'open', 'pricelist_id': order.pricelist_id.id})
                        order.subscription_id.sudo().increment_period()
                    if not order.subscription_management:
                        order.subscription_management = 'upsell'
                    # add new lines or increment quantities on existing lines
                    values = {'recurring_invoice_line_ids': []}
                    for line in order.order_line:
                        if line.product_id.recurring_invoice:
                            recurring_line_id = False
                            if line.product_id in [subscr_line.product_id for subscr_line in order.subscription_id.recurring_invoice_line_ids]:
                                for subscr_line in order.subscription_id.recurring_invoice_line_ids:
                                    if subscr_line.product_id == line.product_id and subscr_line.uom_id == line.product_uom:
                                        recurring_line_id = subscr_line.id
                                        quantity = subscr_line.sold_quantity
                                        break
                            if recurring_line_id:
                                values['recurring_invoice_line_ids'].append((1, recurring_line_id, {
                                    'sold_quantity': quantity + line.product_uom_qty,
                                }))
                            else:
                                values['recurring_invoice_line_ids'].append((0, 0, {
                                    'product_id': line.product_id.id,
                                    'analytic_account_id': order.subscription_id.id,
                                    'name': line.name,
                                    'sold_quantity': line.product_uom_qty,
                                    'uom_id': line.product_uom.id,
                                    'price_unit': line.price_unit,
                                    'discount': line.discount if line.order_id.subscription_management == 'renew' else False,
                                }))
                    order.subscription_id.sudo().write(values)
                order.action_done()
        return res

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.project_id and self.subscription_management == 'renew':
            subscr = self.env['sale.subscription'].search([('analytic_account_id', '=', self.project_id.id)], limit=1)
            next_date = datetime.datetime.strptime(subscr.recurring_next_date, "%Y-%m-%d")
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[subscr.recurring_rule_type]: subscr.recurring_interval})
            previous_date = next_date - invoicing_period

            invoice_vals['comment'] = _("This invoice covers the following period: %s - %s") % (previous_date.date(), (next_date - relativedelta(days=1)).date())

        return invoice_vals
