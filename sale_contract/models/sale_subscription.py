# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _description = "Sale Subscription"
    _inherits = {'account.analytic.account': 'analytic_account_id'}
    _inherit = 'mail.thread'

    state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'To Renew'),
                              ('close', 'Closed'), ('cancel', 'Cancelled')],
                             string='Status', required=True, track_visibility='onchange', copy=False, default='draft')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True, ondelete="cascade", auto_join=True)
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date = fields.Date(string='End Date', track_visibility='onchange')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Currency', readonly=True)
    recurring_invoice_line_ids = fields.One2many('sale.subscription.line', 'analytic_account_id', string='Invoice Lines', copy=True)
    recurring_rule_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ], string='Recurrency', help="Invoice automatically repeat at specified interval", default='monthly')
    recurring_interval = fields.Integer(string='Repeat Every', help="Repeat every (Days/Week/Month/Year)", default=1)
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today)
    recurring_total = fields.Float(compute='_compute_recurring_total', string="Recurring Price", store=True, track_visibility='onchange')
    close_reason_id = fields.Many2one("sale.subscription.close.reason", string="Close Reason", track_visibility='onchange')
    type = fields.Selection([('contract', 'Contract'), ('template', 'Template')], string='Type', default='contract')
    template_id = fields.Many2one('sale.subscription', string='Subscription Template', domain=[('type', '=', 'template')], track_visibility='onchange')
    description = fields.Text()
    user_id = fields.Many2one('res.users', string='Responsible', track_visibility='onchange')
    manager_id = fields.Many2one('res.users', string='Sales Rep', track_visibility='onchange')
        # Fields that only matters on template
    plan_description = fields.Html(help="Describe this subscription in a few lines", sanitize_attributes=False)
    user_selectable = fields.Boolean(string='Allow Online Order', default=True, help="""Leave this unchecked if you don't want this subscription template to be available to the customer in the frontend (for a free trial, for example)""")

    @api.depends('recurring_invoice_line_ids')
    def _compute_recurring_total(self):
        for account in self:
            account.recurring_total = sum(line.price_subtotal for line in account.recurring_invoice_line_ids)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.onchange('template_id')
    def on_change_template(self):
        if self.template_id:
            if not self.ids:
                invoice_line_ids = []
                for x in self.template_id.recurring_invoice_line_ids:
                    invoice_line_ids.append((0, 0, {
                        'product_id': x.product_id.id,
                        'uom_id': x.uom_id.id,
                        'name': x.name,
                        'sold_quantity': x.sold_quantity,
                        'actual_quantity': x.quantity,
                        'price_unit': x.price_unit,
                        'analytic_account_id': x.analytic_account_id and x.analytic_account_id.id or False,
                    }))
                self.recurring_invoice_line_ids = invoice_line_ids
            self.recurring_interval = self.template_id.recurring_interval
            self.recurring_rule_type = self.template_id.recurring_rule_type

    @api.model
    def create(self, vals):
        vals['code'] = vals.get('code') or self.env.context.get('default_code') or self.env['ir.sequence'].next_by_code('sale.subscription') or 'New'
        if vals.get('name', 'New') == 'New':
            vals['name'] = vals['code']
        return super(SaleSubscription, self).create(vals)

    @api.multi
    def name_get(self):
        res = []
        for sub in self:
            if sub.type != 'template':
                name = '%s - %s' % (sub.code, sub.partner_id.name) if sub.code else sub.partner_id.name
                res.append((sub.id, '%s/%s' % (sub.template_id.code, name) if sub.template_id.code else name))
            else:
                name = '%s - %s' % (sub.code, sub.name) if sub.code else sub.name
                res.append((sub.id, name))
        return res

    @api.multi
    def action_subscription_invoice(self):
        analytic_ids = [sub.analytic_account_id.id for sub in self]
        orders = self.env['sale.order'].search_read(domain=[('subscription_id', 'in', self.ids)], fields=['name'])
        order_names = [order['name'] for order in orders]
        invoices = self.env['account.invoice'].search([('invoice_line_ids.account_analytic_id', 'in', analytic_ids),
                                                       ('origin', 'in', self.mapped('code') + order_names)])
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.invoice",
            "views": [[self.env.ref('account.invoice_tree').id, "tree"],
                      [self.env.ref('account.invoice_form').id, "form"]],
            "domain": [["id", "in", invoices.ids]],
            "context": {"create": False},
            "name": "Invoices",
        }

    @api.model
    def cron_account_analytic_account(self):
        remind = {}

        def fill_remind(key, domain, write_pending=False):
            base_domain = [
                ('type', '=', 'contract'),
                ('partner_id', '!=', False),
                ('manager_id', '!=', False),
                ('manager_id.email', '!=', False),
            ]
            base_domain.extend(domain)

            for account in self.search(base_domain, order='name asc'):
                if write_pending:
                    account.write({'state': 'pending'})
                remind_user = remind.setdefault(account.manager_id.id, {})
                remind_type = remind_user.setdefault(key, {})
                remind_partner = remind_type.setdefault(account.partner_id, []).append(account)

        # Already expired
        fill_remind("old", [('state', 'in', ['pending'])])

        # Expires now
        fill_remind("new", [('state', 'in', ['draft', 'open']),
                            '&', ('date', '!=', False), ('date', '<=', fields.Date.today()),
                            ], True)

        # Expires in less than 30 days
        fill_remind("future", [('state', 'in', ['draft', 'open']), ('date', '!=', False), ('date', '<', fields.Date.to_string(fields.Date.from_string(fields.Date.today()) + relativedelta(days=30)))])

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action = self.env.ref('sale_contract.sale_subscription_action')
        template = self.env.ref('sale_contract.account_analytic_cron_email_template')
        for user_id, data in remind.items():
            _logger.debug("Sending reminder to uid %s", user_id)
            template.with_context({'base_url': base_url, 'action_id': action.id, 'data': data}).send_mail(user_id, force_send=True)
        return True

    @api.model
    def _cron_recurring_create_invoice(self):
        return self._recurring_create_invoice(automatic=True)

    @api.multi
    def set_open(self):
        return self.write({'state': 'open', 'date': False})

    @api.multi
    def set_pending(self):
        return self.write({'state': 'pending'})

    @api.multi
    def set_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def set_close(self):
        return self.write({'state': 'close', 'date': fields.Date.from_string(fields.Date.today())})

    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Subscription %s!") % self.name)

        fpos_id = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(self.partner_id.id)
        journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (self.company_id.name or '', ))

        next_date = fields.Date.from_string(self.recurring_next_date)
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        new_date = next_date + relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})

        return {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.pricelist_id.currency_id.id,
            'journal_id': journal.id,
            'date_invoice': self.recurring_next_date,
            'origin': self.code,
            'fiscal_position_id': fpos_id,
            'payment_term_id': self.partner_id.property_payment_term_id.id,
            'company_id': self.company_id.id,
            'comment': _("This invoice covers the following period: %s - %s") % (next_date, new_date),
        }

    def _prepare_invoice_line(self, line, fiscal_position):
        account_id = line.product_id.property_account_income_id.id
        if not account_id:
            account_id = line.product_id.categ_id.property_account_income_categ_id.id
        account_id = fiscal_position.map_account(account_id)

        tax = line.product_id.taxes_id.filtered(lambda r: r.company_id == line.analytic_account_id.company_id)
        tax = fiscal_position.map_tax(tax)
        return {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.analytic_account_id.id,
            'price_unit': line.price_unit or 0.0,
            'discount': line.discount,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id,
            'product_id': line.product_id.id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)],
        }

    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.recurring_invoice_line_ids]

    def _prepare_invoice(self):
        invoice = self._prepare_invoice_data()
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'])
        return invoice

    @api.multi
    def recurring_invoice(self):
        self._recurring_create_invoice()
        return self.action_subscription_invoice()

    @api.returns('account.invoice')
    def _recurring_create_invoice(self, automatic=False):
        AccountInvoice = self.env['account.invoice']
        invoices = []
        current_date = fields.Date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        domain = ['id', 'in', self.ids] if self.ids else [('recurring_next_date', '<=', current_date), ('state', '=', 'open'), ('type', '=', 'contract')]
        sub_data = self.search_read(fields=['id', 'company_id'], domain=domain)
        for company_id in set(data['company_id'][0] for data in sub_data):
            sub_ids = map(lambda s: s['id'], filter(lambda s: s['company_id'][0] == company_id, sub_data))
            subs = self.with_context(company_id=company_id, force_company=company_id).browse(sub_ids)
            for sub in subs:
                try:
                    invoices.append(AccountInvoice.create(sub._prepare_invoice()))
                    invoices[-1].message_post_with_view('mail.message_origin_link',
                     values={'self': invoices[-1], 'origin': sub},
                     subtype_id=self.env.ref('mail.mt_note'))
                    invoices[-1].compute_taxes()
                    next_date = fields.Date.from_string(sub.recurring_next_date or current_date)
                    rule, interval = sub.recurring_rule_type, sub.recurring_interval
                    new_date = next_date + relativedelta(**{periods[rule]: interval})
                    sub.write({'recurring_next_date': new_date})
                    if automatic:
                        self.env.cr.commit()
                except Exception:
                    if automatic:
                        self.env.cr.rollback()
                        _logger.exception('Fail to create recurring invoice for subscription %s', sub.code)
                    else:
                        raise
        return invoices

    def _prepare_renewal_order_values(self):
        res = dict()
        for contract in self:
            order_lines = []
            fpos_id = self.env['account.fiscal.position'].get_fiscal_position(contract.partner_id.id)
            for line in contract.recurring_invoice_line_ids:
                order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.product_tmpl_id.name,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                }))
            res[contract.id] = {
                'pricelist_id': contract.pricelist_id.id,
                'partner_id': contract.partner_id.id,
                'partner_invoice_id': contract.partner_id.id,
                'partner_shipping_id': contract.partner_id.id,
                'currency_id': contract.pricelist_id.currency_id.id,
                'order_line': order_lines,
                'project_id': contract.analytic_account_id.id,
                'subscription_management': 'renew',
                'note': contract.description,
                'user_id': contract.manager_id.id,
                'fiscal_position_id': fpos_id,
            }
        return res

    @api.multi
    def prepare_renewal_order(self):
        self.ensure_one()
        values = self._prepare_renewal_order_values()
        order = self.env['sale.order'].create(values[self.id])
        order.order_line._compute_tax_id()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order.id,
        }

    @api.multi
    def increment_period(self):
        for account in self:
            current_date = account.recurring_next_date or self.default_get(['recurring_next_date'])['recurring_next_date']
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            new_date = fields.Date.from_string(current_date) + relativedelta(**{periods[account.recurring_rule_type]: account.recurring_interval})
            account.write({'recurring_next_date': new_date})

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        partners = self.env['res.partner'].search([('name', operator, name)], limit=limit)
        if partners:
            domain = ['|'] + domain + [('partner_id', 'in', partners.ids)]
        rec = self.search(domain + args, limit=limit)
        return rec.name_get()


class SaleSubscriptionLine(models.Model):
    _name = "sale.subscription.line"

    product_id = fields.Many2one('product.product', string='Product', domain="[('recurring_invoice','=',True)]", required=True)
    analytic_account_id = fields.Many2one('sale.subscription', string='Subscription')
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(compute='_compute_quantity', inverse='_set_quantity', string='Quantity', store=True,
                            help="Max between actual and sold quantities; this quantity will be invoiced")
    actual_quantity = fields.Float(help="Quantity actually used by the customer", default=0.0)
    sold_quantity = fields.Float(help="Quantity sold to the customer", required=True, default=1)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'))
    price_subtotal = fields.Float(compute='_compute_price_subtotal', string='Sub Total', digits=dp.get_precision('Account'))

    @api.depends('sold_quantity', 'actual_quantity')
    def _compute_quantity(self):
        for line in self:
            line.quantity = max(line.sold_quantity, line.actual_quantity)

    def _set_quantity(self):
        for line in self:
            line.actual_quantity = line.quantity

    @api.depends('price_unit', 'quantity', 'discount', 'analytic_account_id.pricelist_id')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit * (100.0 - line.discount) / 100.0
            if line.analytic_account_id.pricelist_id:
                line.price_subtotal = line.analytic_account_id.pricelist_id.currency_id.round(line.price_subtotal)

    @api.onchange('product_id')
    def onchange_product_id(self):
        domain = {}
        contract = self.analytic_account_id
        company_id = contract.company_id.id
        pricelist_id = contract.pricelist_id.id
        context = dict(self.env.context, company_id=company_id, force_company=company_id, pricelist=pricelist_id)
        if not self.product_id:
            self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            partner = contract.partner_id.with_context(context)
            if partner.lang:
                context.update({'lang': partner.lang})

            product = self.product_id.with_context(context)
            self.price_unit = product.price

            name = product.display_name
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name

            if not self.uom_id:
                self.uom_id = product.uom_id.id
            if self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

        return {'domain': domain}

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        if not self.uom_id:
            self.price_unit = 0.0
        else:
            self.onchange_product_id()


class SaleSubscriptionCloseReason(models.Model):
    _name = "sale.subscription.close.reason"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
