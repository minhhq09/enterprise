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
        'views/yodlee_views.xml',
    ],
    'init_xml': [
        'data/online.institution.csv',
    ],
    'qweb': [
        'views/yodlee_templates.xml',
    ],
}
