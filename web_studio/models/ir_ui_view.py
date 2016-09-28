# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import json


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def create(self, vals):
        res = super(View, self).create(vals)

        if self._context.get('studio'):
            res.create_studio_model_data(res.name)

        return res

    def _apply_group(self, model, node, modifiers, fields):
        # apply_group only returns the view groups ids.
        # As we need also need their name and display in Studio to edit these groups
        # (many2many widget), they have been added to node (only in Studio).
        if self._context.get('studio'):
            if node.get('groups'):
                studio_groups = []
                for xml_id in node.attrib['groups'].split(','):
                    group = self.env['ir.model.data'].xmlid_to_object(xml_id)
                    if group:
                        studio_groups.append({
                            "id": group.id,
                            "name": group.name,
                            "display_name": group.display_name
                        })
                node.attrib['studio_groups'] = json.dumps(studio_groups)

        return super(View, self)._apply_group(model, node, modifiers, fields)
