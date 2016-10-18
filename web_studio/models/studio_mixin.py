# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StudioMixin(models.AbstractModel):
    """ Mixin that overrides the create and write methods to properly generate
        ir.model.data entries flagged with Studio for the corresponding resources.
    """
    _name = 'studio.mixin'

    @api.model
    def create(self, vals):
        res = super(StudioMixin, self).create(vals)

        if self._context.get('studio'):
            res.create_studio_model_data()

        return res

    @api.multi
    def write(self, vals):
        res = super(StudioMixin, self).write(vals)

        if self._context.get('studio'):
            for record in self:
                record.create_studio_model_data()

        return res
