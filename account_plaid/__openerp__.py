# -*- coding: utf-8 -*-
{
    'name': "account_plaid",

    'summary': """
        Use Plaid.com to retrieve bank statements""",

    'description': """
        Use Plaid.com to retrieve bank statements.
    """,

    'author': "OpenERP s.a.",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_online_synch'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/plaid_views.xml',
    ],
    'qweb': [
        'views/plaid_templates.xml',
    ],
}
