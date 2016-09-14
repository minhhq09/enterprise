# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
import re

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = ['helpdesk.ticket']

    access_token = fields.Char(
        'Security Token', copy=False, default=lambda self: str(uuid.uuid4()),
        required=True)

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        if not self.team_id.website_published:
            return super(HelpdeskTicket, self).get_access_action()
        return {
            'type': 'ir.actions.act_url',
            'url': '/ticket/%s' % self.id,
            'target': 'self',
            'res_id': self.id,
        }


class HelpdeskTeam(models.Model):

    _name = "helpdesk.team"
    _inherit = ['helpdesk.team', 'website.published.mixin']

    @api.onchange('use_website_helpdesk_form', 'use_website_helpdesk_forum', 'use_website_helpdesk_slides')
    def _onchange_use_website_helpdesk(self):
        if not (self.use_website_helpdesk_form or self.use_website_helpdesk_forum or self.use_website_helpdesk_slides) and self.website_published:
            self.website_published = False

    @api.multi
    def _compute_website_url(self):
        for team in self:
            team.website_url = "/helpdesk/" + re.sub('\W+', '-', team.name) + '-' + str(team.id)
