# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Form Helpdesk',
    'category': 'Helpdesk',
    'sequence': 10,
    'summary': 'Helpdesk form to submit a ticket from your website',
    'depends': [
        'website_helpdesk',
    ],
    'description': """Generic web forms to use submit a Ticket""",
    'data': [
        'data/website_helpdesk.xml',
        'views/helpdesk_views.xml',
        'views/helpdesk_templates.xml'
    ],
}
