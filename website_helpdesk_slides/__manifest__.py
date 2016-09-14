# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Slides Helpdesk',
    'category': 'Helpdesk',
    'sequence': 10,
    'summary': 'Ticketing, Support, Slides',
    'depends': [
        'website_helpdesk',
        'website_slides',
    ],
    'description': """
Website Slides integration into helpdesk module
===============================================

    """,
    'data': [
        'views/helpdesk_views.xml',
        'views/helpdesk_templates.xml',
        'wizard/slide_upload_views.xml'
    ],
    'auto_install': True,
}
