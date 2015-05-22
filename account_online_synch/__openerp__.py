# -*- coding: utf-8 -*-
{
    'name': "account_online_synch",

    'summary': """
        This module is used for Online bank synchronization.""",

    'description': """
        This module is used for Online bank synchronization. It provides basic methods to synchronize bank statement.
    """,

    'author': "OpenERP S.A.",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_accountant'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/online_synch_views.xml',
    ],
}
