# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models


class sale_order(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"

    def create_contract(self):
        """ Create a contract based on the order's quote template's contract template """
        self.ensure_one()
        if self.require_payment:
            tx = self.env['payment.transaction'].search([('reference', '=', self.name)])
            payment_method = self.env['payment.method'].search([('acquirer_ref', '=', tx.partner_reference)])
        if self.template_id and self.template_id.contract_template and not self.project_id:
            values = self._prepare_contract_data(payment_method_id=payment_method.id if self.require_payment else False)
            account = self.env['account.analytic.account'].sudo().create(values)
            account.name = self.partner_id.name + ' - ' + account.code

            invoice_line_ids = []
            for line in self.order_line:
                if line.product_id.recurring_invoice:
                    invoice_line_ids.append((0, 0, {
                        'product_id': line.product_id.id,
                        'analytic_account_id': account.id,
                        'name': line.name,
                        'sold_quantity': line.product_uom_qty,
                        'discount': line.discount,
                        'uom_id': line.product_uom.id,
                        'price_unit': line.price_unit,
                    }))
            if invoice_line_ids:
                analytic_values = {'recurring_invoice_line_ids': invoice_line_ids}
                account.write(analytic_values)

            self.project_id = account
            # send new contract email to partner
            _, template_id = self.env['ir.model.data'].get_object_reference('website_contract', 'email_contract_open')
            mail_template = self.env['mail.template'].browse(template_id)
            mail_template.send_mail(account.id, force_send=True)
            return account
        return False

    def _prepare_contract_data(self, payment_method_id=False):
        contract_tmp = self.template_id.contract_template
        values = {
            'name': contract_tmp.name,
            'state': 'open',
            'type': 'contract',
            'template_id': contract_tmp.id,
            'partner_id': self.partner_id.id,
            'manager_id': self.user_id.id,
            'contract_type': contract_tmp.contract_type,
            'date_start': fields.Date.today(),
            'quantity_max': contract_tmp.quantity_max,
            'parent_id': contract_tmp.parent_id and contract_tmp.parent_id.id or False,
            'description': self.note,
            'payment_method_id': payment_method_id,
            'pricelist_id': self.pricelist_id.id,
        }
        if 'asset_category_id' in contract_tmp._fields:
            values.update({'asset_category_id': contract_tmp.asset_category_id and contract_tmp.asset_category_id.id})
        if values['contract_type'] == 'subscription':
            values.update({
                'recurring_rule_type': contract_tmp.recurring_rule_type,
                'recurring_interval': contract_tmp.recurring_interval,
            })
            # compute the next invoice date
            today = datetime.date.today()
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
            recurring_next_date = today + invoicing_period
            values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        return values

    @api.one
    def action_button_confirm(self):
        res = super(sale_order, self).action_button_confirm()
        self.create_contract()
        return res

    # DBO: the following is there to amend the behaviour of website_sale:
    # - do not update price on sale_order_line where force_price = True
    #   (some options may have prices that are different from the product price)
    # - prevent having a cart with options for different contracts (project_id)
    # If we ever decide to move the payment code out of website_sale, we should scrap all this
    def set_project_id(self, account_id):
        """ Set the specified account_id account.analytic.account as the sale_order project_id
        and remove all the recurring products from the sale order if the field was already defined"""
        data = []
        account = self.env['account.analytic.account'].browse(account_id)
        if self.project_id != account:
            self.reset_project_id()
        self.write({'project_id': account.id, 'user_id': account.manager_id.id if account.manager_id else False})

    def reset_project_id(self):
        """ Remove the project_id of the sale order and remove all sale.order.line whose
        product is recurring"""
        data = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.recurring_invoice:
                data.append((2, line.id))
        self.write({'order_line': data, 'project_id': False})

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, line_id=None, context=None):
        res = super(sale_order, self)._website_product_id_change(cr, uid, ids, order_id, product_id, qty, line_id, context=context)
        if line_id:
            line = self.pool['sale.order.line'].browse(cr, uid, line_id, context=context)
            if line.force_price:
                forced_price = line.price_unit
                res['price_unit'] = forced_price
        return res


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _name = "sale.order.line"

    force_price = fields.Boolean('Force price', help='Force a specific price, regardless of any coupons or pricelist change', default=False)

    @api.multi
    def button_confirm(self):
        lines = []
        account = False
        for line in self:
            account = line.order_id.project_id
            if line.order_id.project_id and line.product_id.recurring_invoice:
                lines.append(line)
        cr, uid, context = self.env.cr, self.env.uid, self.env.context
        msg_body = self.pool['ir.ui.view'].render(cr, uid, ['website_contract.chatter_add_paid_option'],
                                                      values={'lines': lines},
                                                      context=context)
        account and account.message_post(body=msg_body)
        return super(sale_order_line, self).button_confirm()

    @api.model
    def _prepare_order_line_invoice_line(self, line, account_id=False):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(line, account_id=account_id)
        if 'asset_category_id' in self.env['account.analytic.account']._fields:
            if line.order_id.template_id and line.order_id.template_id.contract_template:
                if line.order_id.template_id.contract_template.asset_category_id and line.product_id.recurring_invoice:
                    res.update({'asset_category_id': line.order_id.template_id.contract_template.asset_category_id.id})
        return res
