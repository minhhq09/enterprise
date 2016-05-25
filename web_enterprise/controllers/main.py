# -*- coding: utf-8 -*-

import json

import werkzeug.utils
import werkzeug.wrappers

import openerp
import openerp.modules.registry
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import ensure_db

#----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
#----------------------------------------------------------
openerp.release.version_info = version_info = openerp.release.version_info[:5] + ('e',)
version_split = openerp.release.version.split('-', 1)
openerp.release.version = (version_split[0][:-1] + version_info[5] +
                           ('-%s' % version_split[1] if len(version_split) > 1 else ''))
openerp.service.common.RPC_VERSION_1.update(
    server_version=openerp.release.version,
    server_version_info=openerp.release.version_info)

#----------------------------------------------------------
# OpenERP Web web Controllers
#----------------------------------------------------------
class Home(http.Controller):

    # ideally, this route should be `auth="user"` but that don't work in non-monodb mode.
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        context = {
            'session_info': json.dumps(request.env['ir.http'].session_info()),
        }
        return request.render('web.webclient_bootstrap', qcontext=context)
