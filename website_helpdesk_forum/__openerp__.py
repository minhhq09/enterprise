# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk: Knowledge Base',
    'category': 'Helpdesk',
    'sequence': 10,
    'summary': 'Knowledge base for helpdesk',
    'depends': [
        'website_forum',
        'website_helpdesk'
    ],
    'description': 'Knowledge base for helpdesk based on Odoo Forum',
    'data': [
        'views/helpdesk_templates.xml',
        'views/helpdesk_views.xml',
    ],
    'auto_install': True,
}
