# -*- coding: utf-8 -*-
{
    'name': "Google Cloud Messaging",
    'version': "1.0",
    'description': """
Google Cloud Messaging Integration
==================================
This module allows to send GCM push notification on registered devices
for every message received in a chat and for every mentions.

**Configure your API keys from General Setting**
    """,
    'depends': ['mail_cloud_notification'],
    'external_dependencies': {'python': ['gcm']},
    'data': [
        'views/res_config.xml',
        'views/assets.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
