# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import unicodedata

from odoo import api, models
from odoo.tools import ustr


def sanitize_for_xmlid(s):
    """ Transform a string to a name suitable for use in xml_id.
        For example, My new application -> my_new_application.
        It will process string by stripping leading and ending spaces,
        converting unicode chars to ascii, lowering all chars and replacing spaces
        with underscore.
        :param s: str
        :rtype: str
    """
    s = ustr(s)
    uni = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

    slug_str = re.sub('[\W]', ' ', uni).strip().lower()
    slug_str = re.sub('[-\s]+', '_', slug_str)
    return slug_str


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    @api.model
    def create_or_get_studio_module(self, menu_id=None, description=None):

        if menu_id:
            root_menu = self.env['ir.ui.menu'].browse([menu_id])
            model_data = self.env['ir.model.data'].search([['res_id', '=', root_menu.id], ['model', '=', 'ir.ui.menu']])

            if model_data and model_data.module.startswith('studio_custom_app_'):
                # this is an application made by Studio, so all modifications
                # should be made in the same module
                module_name = model_data.module
            else:
                # this is a customization for an existing application
                module_name = 'studio_customization_%s' % (model_data.module or 'web_studio')
                module_description = root_menu.name
                is_app = False
        else:
            # this is a totally new application
            module_name = 'studio_custom_app_%s' % sanitize_for_xmlid(description)
            module_description = description
            is_app = True

        if not self.search_count([['name', '=', module_name]]):
            # need to create a module from scratch
            self.create({
                'name': module_name,
                'application': is_app,
                'shortdesc': module_description,
                'state': 'installed',
                'imported': True,
            })

        return module_name
