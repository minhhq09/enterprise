# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    eco_inprogress = fields.Boolean('ECO in progress?', compute='_compute_eco_data')
    eco_inprogress_count = fields.Integer('# ECOs in progress', compute='_compute_eco_data')

    @api.multi
    def _compute_eco_data(self):
        eco_data = self.env['mrp.eco'].read_group([
            ('product_tmpl_id', 'in', self.ids),
            ('state', '=', 'progress')],
            ['product_tmpl_id'], ['product_tmpl_id'])
        result = dict((data['product_tmpl_id'][0], data['product_tmpl_id_count']) for data in eco_data)
        for eco in self:
            eco.eco_inprogress_count = result.get(eco.id, 0)
            eco.eco_inprogress = bool(eco.eco_inprogress_count)
