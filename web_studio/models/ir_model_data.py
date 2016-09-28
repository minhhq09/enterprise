# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    studio = fields.Boolean(help='Checked if it has been edited with Studio.')

    def set_studio_modification(self):
        """ When editing an ir.model.data with Studio, we put it in noupdate to
                avoid the customizations to be dropped when upgrading the module.
        """
        self.write({
            'noupdate': True,
            'studio': True,
        })
