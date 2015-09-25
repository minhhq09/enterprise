# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from datetime import datetime


class report_account_coa(models.AbstractModel):
    _name = "account.coa.report"
    _description = "Chart of Account Report"
    _inherit = "account.general.ledger"

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['account.context.coa'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'state': context_id.all_entries and 'all' or 'posted',
            'cash_basis': context_id.cash_basis,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
        })
        return self.with_context(new_context)._lines(line_id)

    @api.model
    def _lines(self, line_id=None):
        lines = []
        context = self.env.context
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_accounts = self.with_context(date_from_aml=context['date_from'], date_from=context['date_from'] and company_id.compute_fiscalyear_dates(datetime.strptime(context['date_from'], "%Y-%m-%d"))['date_from'] or None).group_by_account_id(line_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        title_index = 0
        for account in sorted_accounts:
            if int(account.code[0]) > title_index:
                title_index = int(account.code[0])
                lines.append({
                    'id': title_index,
                    'type': 'line',
                    'name': _("Class %s" % (title_index)),
                    'footnotes': [],
                    'columns': ['', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': True,
                })
            lines.append({
                'id': account.id,
                'type': 'account_id',
                'name': account.code + " " + account.name,
                'footnotes': self.env.context['context_id']._get_footnotes('account_id', account.id),
                'columns': [grouped_accounts[account]['balance'] > 0 and self._format(grouped_accounts[account]['debit'] - grouped_accounts[account]['credit']) or '',
                            grouped_accounts[account]['balance'] < 0 and self._format(grouped_accounts[account]['credit'] - grouped_accounts[account]['debit']) or ''],
                'level': 1,
                'unfoldable': False,
            })
        return lines

    @api.model
    def get_title(self):
        return _("Chart of Account")

    @api.model
    def get_name(self):
        return 'coa'

    @api.model
    def get_report_type(self):
        return 'no_date_range'


class account_context_coa(models.TransientModel):
    _name = "account.context.coa"
    _description = "A particular context for the chart of account"
    _inherit = "account.report.context.common"

    fold_field = 'unfolded_accounts'
    unfolded_accounts = fields.Many2many('account.account', 'context_to_account_coa', string='Unfolded lines')

    def get_report_obj(self):
        return self.env['account.coa.report']

    def get_columns_names(self):
        return [_("Debit"), _("Credit")]

    @api.multi
    def get_columns_types(self):
        return ["number", "number"]
