from openerp import models, fields, api


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _inherit = "sale.subscription"

    asset_category_id = fields.Many2one('account.asset.category', 'Deferred Revenue Category',
                                        help="This asset category will be applied to the lines of the contract's invoices.",
                                        domain="[('type','=','sale')]")
    template_asset_category_id = fields.Many2one('account.asset.category', 'Deferred Revenue Category',
                                        help="This asset category will be applied to the subscriptions based on this template. This field is company-dependent.",
                                        domain="[('type','=','sale')]", company_dependent=True)

    @api.multi
    def on_change_template(self, template_id):
        res = super(SaleSubscription, self).on_change_template(template_id)

        template = self.browse(template_id)
        if template.template_asset_category_id:
            res['value']['asset_category_id'] = template.template_asset_category_id.id

        return res

    @api.model
    def _prepare_invoice_lines(self, contract, fiscal_position_id):
        inv_lines = super(SaleSubscription, self)._prepare_invoice_lines(contract, fiscal_position_id)

        for line in inv_lines:
            if contract.asset_category_id:
                line[2]['asset_category_id'] = contract.asset_category_id.id
            elif line[2].get('product_id'):
                Product = self.env['product.product'].browse([line[2]['product_id']])
                line[2]['asset_category_id'] = Product.product_tmpl_id.deferred_revenue_category_id.id

        return inv_lines


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
            For recurring products, add the deferred revenue category on the invoice line
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.product_id.recurring_invoice and self.order_id.subscription_id.asset_category_id:
            res['asset_category_id'] = self.order_id.subscription_id.asset_category_id.id
        return res
