# -*- coding: utf-8 -*-
from openerp import fields, models, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _query_get(self, domain=None):
        tables, where_clause, where_params = super(AccountMoveLine, self)._query_get(domain=domain)
        financial_report = self.env.context.get('financial_report')
        if financial_report and financial_report.tax_report:
            where_clause += ''' AND "account_move_line".tax_exigible = 't' '''
        return tables, where_clause, where_params

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"
    _description = "Account Report"

    tax_report = fields.Boolean('Tax Report', help="Set to True to automatically filter out journal items that have the boolean field ´tax_exigible´ set to False")

class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"
    _description = "Account Report Line"

    # FORWARD-PORT UP TO SAAS-12
    def _insert_tax_exigible(self):
        return ['\"account_move_line\".tax_exigible, ', 'aml.tax_exigible, ']

    def _eval_formula(self, financial_report, debit_credit, context, currency_table, linesDict):
        self = self.with_context(financial_report=financial_report)
        return super(AccountFinancialReportLine, self)._eval_formula(financial_report, debit_credit, context, currency_table, linesDict)

class report_account_generic_tax_report(models.AbstractModel):
    _inherit = "account.generic.tax.report"
    _description = "Generic Tax Report"

    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s AND "account_move_line".tax_exigible GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s AND "account_move_line".tax_exigible GROUP BY r.account_tax_id"""
        return sql
