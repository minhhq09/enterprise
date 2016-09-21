# -*- coding: utf-8 -*-
{
    'name': "Project Forecast",

    'summary': """Resource management for Project""",

    'description': """
    Resource management for Project
    """,
    'category': 'Project',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['project'],

    # always loaded
    'data': [
        'data/project_forecast_data.xml',
        'security/ir.model.access.csv',
        'security/project_forecast_security.xml',
        'views/project_forecast_views.xml',
        'views/project_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/project_forecast_demo.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
}
