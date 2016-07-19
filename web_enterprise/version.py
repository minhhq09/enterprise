# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

# ----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
# ----------------------------------------------------------
odoo.release.version_info = version_info = odoo.release.version_info[:5] + ('e',)
version_split = odoo.release.version.split('-', 1)
odoo.release.version = (version_split[0][:-1] + version_info[5] +
                           ('-%s' % version_split[1] if len(version_split) > 1 else ''))
odoo.service.common.RPC_VERSION_1.update(
    server_version=odoo.release.version,
    server_version_info=odoo.release.version_info)
