# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    name = fields.Char(string='Analytic Account', index=True, required=True, track_visibility='onchange', default='New')
    code = fields.Char(string='Reference', index=True, track_visibility='onchange', default=lambda self: self.env['ir.sequence'].next_by_code('sale.subscription') or 'New')
    subscription_ids = fields.One2many('sale.subscription', 'analytic_account_id', string='Subscriptions')
    subscription_count = fields.Integer(compute='_compute_subscription_count', string='Susbcription Count')

    def _compute_subscription_count(self):
        for account in self:
            account.subscription_count = len(account.subscription_ids)

    @api.multi
    def subscriptions_action(self):
        subscription_ids = self.mapped('subscription_ids').ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "sale.subscription",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "in", subscription_ids]],
            "context": {"create": False},
            "name": "Subscriptions",
        }
        if len(subscription_ids) == 1:
            result['views'] = [(False, "form")]
            result['res_id'] = subscription_ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
