# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tax exigible enterprise',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
    Fix the tax reports to exclude the not exigible amounts (operations with a cash based tax, not yet paid). Backport of bdd1fe4
    """,
    'depends': ['account_reports', 'account_tax_exigible'],
    'data': [
        'views/view.xml',
    ],
    'test': [],
    'demo': [],
    'auto_install': True,
    'installable': True,
    'post_init_hook': '_load_data',
    'license': 'OEEL-1',
}
