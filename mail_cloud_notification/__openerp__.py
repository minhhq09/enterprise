# -*- coding: utf-8 -*-
{
    'name': "Cloud Notifiacion Base Module",
    'version': "1.0",
    'description': """
Base Module For Cloud Notifiacion
=================================
This module will be base of cloud notification integration like GCM, APN, Firebase
    """,
    'depends': ['mail', 'mobile'],
    'data': [
        'views/res_partner.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}
