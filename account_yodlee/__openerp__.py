# -*- coding: utf-8 -*-
{
    'name': "Yodlee",
    'summary': "Yodlee Finance",
    'author': "Odoo S.A.",
    'website': "https://www.odoo.com",
    'category': 'Accounting &amp; Finance',
    'version': '1.0',
    'depends': ['account_online_sync', 'account_plaid'],
    'description': '''
Sync your bank feeds with Yodlee
================================

Yodlee interface.
''',
    'data': [
        'views/yodlee_views.xml',
    ],
    'init_xml': [
        'data/online.institution.csv',
    ],
    'qweb': [
        'views/yodlee_templates.xml',
    ],
    'license': 'OEEL-1',
}
