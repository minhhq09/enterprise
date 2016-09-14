# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HelpdeskTeam(models.Model):

    _inherit = 'helpdesk.team'

    website_rating_url = fields.Char('URL to Submit Issue', readonly=True, compute='_compute_website_rating_url')

    def _compute_website_rating_url(self):
        for team in self.filtered(lambda team: team.name and team.use_website_helpdesk_rating and team.id):
            team.website_rating_url = (team.use_website_helpdesk_rating and team.id) and ('/helpdesk/rating/' + team.name + '-' + str(team.id)) or False

    @api.multi
    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website team page """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Helpdesk Rating Page",
            'target': 'self',
            'url': "/helpdesk/rating/%s" % (self.id,)
        }
