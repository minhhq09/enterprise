# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os

from openerp import http
from openerp.http import request

class GovCertificationController(http.Controller):
    @http.route('/fdm_source', auth='public')
    def handler(self):
        data = {'files': []}
        relative_file_paths_to_show = [
            "pos_blackbox_be/data/pos_blackbox_be_data.xml",
            "pos_blackbox_be/models/pos_blackbox_be.py",
            "pos_blackbox_be/security/ir.model.access.csv",
            "pos_blackbox_be/security/pos_blackbox_be_security.xml",
            "pos_blackbox_be/static/lib/sha1.js",
            "pos_blackbox_be/static/src/css/pos_blackbox_be.css",
            "pos_blackbox_be/static/src/js/pos_blackbox_be.js",
            "pos_blackbox_be/static/src/xml/pos_blackbox_be.xml",
            "pos_blackbox_be/views/pos_blackbox_be_assets.xml",
            "pos_blackbox_be/views/pos_blackbox_be_views.xml",
            "pos_blackbox_be/controllers/main.py",
            "hw_scanner/controllers/main.py",
            "hw_scale/controllers/main.py",
            "hw_blackbox_be/controllers/main.py"
        ]

        for relative_file_path in relative_file_paths_to_show:
            absolute_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, relative_file_path))
            size_in_bytes = os.path.getsize(absolute_file_path)

            with open(absolute_file_path, 'r') as f:
                data['files'].append({
                    'name': relative_file_path,
                    'size_in_bytes': size_in_bytes,
                    'contents': f.read()
                })

        return request.render('pos_blackbox_be.fdm_source', data, mimetype='text/plain')
