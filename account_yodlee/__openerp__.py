# -*- coding: utf-8 -*-
{
    'name': "account_yodlee",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Your Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['account_online_sync'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/yodlee_views.xml',
    ],
    'qweb': [
        'views/yodlee_templates.xml',
    ],
}
