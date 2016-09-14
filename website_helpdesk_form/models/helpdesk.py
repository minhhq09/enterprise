# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = ['helpdesk.team']

    feature_form_url = fields.Char('URL to Submit Issue', readonly=True, compute='_get_form_url')

    def _get_form_url(self):
        for team in self.filtered(lambda team: team.name and team.use_website_helpdesk_form and team.id):
            name = re.sub('\W+', '-', team.name) + '-' + str(team.id)
            team.feature_form_url = (team.use_website_helpdesk_form and team.id) and ('/helpdesk/' + name + '/submit') or False
