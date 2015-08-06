# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class res_partner(models.Model):
    _inherit = "res.partner"

    ebay_id = fields.Char('eBay User ID')
