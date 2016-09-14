# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website IM Livechat Helpdesk',
    'category': 'Helpdesk',
    'sequence': 10,
    'summary': 'Ticketing, Support, Livechat',
    'depends': [
        'helpdesk',
        'website_livechat',
    ],
    'description': """
Website IM Livechat integration into helpdesk module
====================================================

    """,
    'data': [
        'views/helpdesk_view.xml',
    ],
    'auto_install': True,
}
