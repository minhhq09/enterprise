# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk',
    'version': '1.1',
    'category': 'Helpdesk',
    'sequence': 10,
    'summary': 'Ticketing, Support, Issues',
    'depends': [
        'base_setup',
        'mail',
        'utm',
        'rating'
    ],
    'description': """
Omnichannel Helpdesk
====================

    """,
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_data.xml',
        'data/helpdesk_cron.xml',
        'views/helpdesk_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_ticket_report_views.xml',
        'views/helpdesk_dashboard_views.xml',
    ],
    'qweb': [
        "static/src/xml/helpdesk_dashboard_views.xml",
    ],
    'demo': ['data/helpdesk_demo.xml'],
    'application': True,
}
