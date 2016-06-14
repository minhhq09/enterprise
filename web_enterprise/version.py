# -*- coding: utf-8 -*-

import openerp

# ----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
# ----------------------------------------------------------
openerp.release.version_info = version_info = openerp.release.version_info[:5] + ('e',)
version_split = openerp.release.version.split('-', 1)
openerp.release.version = (version_split[0][:-1] + version_info[5] +
                           ('-%s' % version_split[1] if len(version_split) > 1 else ''))
openerp.service.common.RPC_VERSION_1.update(
    server_version=openerp.release.version,
    server_version_info=openerp.release.version_info)
