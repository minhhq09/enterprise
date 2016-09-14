# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Rating Helpdesk Tickets',
    'version': '1.1',
    'category': 'Website',
    'complexity': 'easy',
    'description': """
This module displays helpdesk team customer satisfaction on your website.
=========================================================================
    """,
    'depends': [
        'website_helpdesk',
    ],
    'data': [
        'views/website_helpdesk_rating_templates.xml',
        'views/helpdesk_views.xml',
    ],
    'installable': True,
    'auto_install': True
}
