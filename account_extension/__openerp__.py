# -*- coding: utf-8 -*-
{
    'name': "Account Extension",
    'summary': """Add some extension to account modules for enterprise version""",
    'description': """
        Add to res_config of account modules the possibility to install extra accounting modules

        This module will be auto installed if account module and enterprise version are present
    """,
    'author': "Odoo SA",
    'category': 'Accounting &amp; Finance',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'views/account_report_menu_invisible.xml',
        'views/res_config_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
