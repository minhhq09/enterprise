# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    name = fields.Char(translate=True)

class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    name = fields.Char(translate=True)
