# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ProductTicCategory(models.Model):
    _name = 'product.tic.category'
    _descrition = "TaxCloud Taxabilty information code for Product Category."
    _rec_name = 'code'

    code = fields.Integer(string="TIC Category Code")
    description = fields.Char(string='TIC Description')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('description', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self):
        res = []
        for category in self:
            res.append((category.id, _('[%s] %s') % (category.code, category.description[0:50])))
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tic_category_id = fields.Many2one('product.tic.category', string="TIC Category")

class ResCompany(models.Model):
    _inherit = 'res.company'

    tic_category_id = fields.Many2one('product.tic.category', string='Default TIC Code', help="Default TICs(Taxabilty information codes) code to get sales tax from TaxCloud by product category.")
