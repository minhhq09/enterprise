# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model
    def create(self, vals):
        res = super(IrActionsActWindow, self).create(vals)

        if self._context.get('studio'):
            res.create_studio_model_data()

        return res
