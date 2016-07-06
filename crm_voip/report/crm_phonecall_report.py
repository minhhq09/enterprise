# -*- coding: utf-8 -*-

from openerp import models, fields, tools


class crm_phonecall_report(models.Model):
    _name = "crm.phonecall.report"
    _description = "Phone Calls by user and team"
    _auto = False

    user_id = fields.Many2one('res.users', 'Responsible', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Contact', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    duration = fields.Float('Duration', digits=(16, 2), group_operator="avg", readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', select=True,
        help="Sales team to which Case belongs to.")
    categ_id = fields.Many2one('crm.phonecall.category', 'Category')
    state = fields.Selection([
        ('pending', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('open', 'To Do'),
        ('done', 'Held')
    ], 'Status', readonly=True)
    date = fields.Datetime('Date', readonly=True, select=True)
    nbr = fields.Integer('# of Cases', readonly=True)

    def init(self, cr):

        """ Phone Calls By User And Team
            @param cr: the current row, from the database cursor,
        """
        tools.drop_view_if_exists(cr, 'crm_phonecall_report')
        cr.execute("""
            create or replace view crm_phonecall_report as (
                select
                    id,
                    c.state,
                    c.user_id,
                    c.team_id,
                    c.categ_id,
                    c.partner_id,
                    c.duration,
                    c.company_id,
                    c.priority,
                    1 as nbr,
                    c.date
                from
                    crm_phonecall c
                where
                    c.state = 'done'
            )""")
