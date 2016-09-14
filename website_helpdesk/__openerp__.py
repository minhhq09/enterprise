# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Helpdesk',
    'category': 'Hidden',
    'summary': 'Generic controller, templates for website',
    'description': 'Generic controller for web',
    'depends': [
        'website_form_editor',
        'helpdesk',
        'website_portal'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/helpdesk_security.xml',
        'views/helpdesk_templates.xml',
        'views/helpdesk_views.xml'
    ],
}
