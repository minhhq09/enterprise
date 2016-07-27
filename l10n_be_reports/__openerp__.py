# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting Reports',
    'version': '1.1',
    'category': 'Localization',
    'description': """
        Accounting reports for Belgium
    """,
    'depends': [
        'l10n_be', 'account_reports'
    ],
    'data': [
        'data/account_financial_html_report_data.xml',
        'views/l10n_be_vat_statement_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/page/accounting',
    'license': 'OEEL-1',
}
