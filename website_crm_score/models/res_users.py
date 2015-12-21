# -*- coding: utf-8 -*-

from openerp import api, fields, models


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    team_user_ids = fields.One2many(
        'team.user', 'user_id',
        string="Sales Records")
    # redefinition of the field defined in sales_team. The field is now computed
    # based on the new modeling introduced in this module. It is stored to avoid
    # breaking the member_ids inverse field. As the relationship between users
    # and sales team is a one2many / many2one relationship we take the first of
    # the team.user record to find the user sales team.
    sale_team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        related='team_user_ids.team_id',
        store=True)
