# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Forecast Grid View",
    'summary': "Add Grid view on Project Forecasts",
    'description': """Bridge module between Project Forecast and Grid View
""",
    'category': 'Project Management',
    'version': '1.0',
    'depends': ['project_forecast', 'grid'],
    'data': [
        'views/views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'auto_install': True,
}
