from openerp import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_count = fields.Integer(string='Subscriptions', compute='_subscription_count')

    @api.multi
    def _subscription_count(self):
        for partner in self:
            partner.subscription_count = self.env['sale.subscription'].search_count([('partner_id', '=', partner.id)])
