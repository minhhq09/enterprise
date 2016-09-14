# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import datetime
from werkzeug.exceptions import NotFound


class WebsiteRatingHelpdesk(http.Controller):

    @http.route(['/helpdesk/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        teams = request.env['helpdesk.team'].sudo().search([('use_rating', '=', True), ('use_website_helpdesk_rating', '=', True)])
        values = {'teams': teams}
        return request.render('website_helpdesk_rating.index', values)

    @http.route(['/helpdesk/rating/<model("helpdesk.team"):team>'], type='http', auth="public", website=True)
    def page(self, team, project_id=None, **kw):
        user = request.env.user
        # to avoid giving any access rights on helpdesk team to the public user, let's use sudo
        # and check if the user should be able to view the team (team managers only if it's not published or has no rating)
        if not (team.use_rating and team.use_website_helpdesk_rating) and not user.sudo(user).has_group('helpdesk.group_helpdesk_manager'):
            raise NotFound()
        tickets = request.env['helpdesk.ticket'].sudo().search([('team_id', '=', team.id)])
        domain = [('res_model', '=', 'helpdesk.ticket'), ('res_id', 'in', tickets.ids)]
        ratings = request.env['rating.rating'].search(domain, order="id desc", limit=100)

        yesterday = (datetime.date.today()-datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
        stats = {}
        for x in (7, 30, 90):
            todate = (datetime.date.today()-datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
            domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
            stats[x] = {1: 0, 5: 0, 10: 0}
            rating_stats = request.env['rating.rating'].read_group(domdate, [], ['rating'])
            total = reduce(lambda x, y: y['rating_count']+x, rating_stats, 0)
            for rate in rating_stats:
                stats[x][rate['rating']] = (rate['rating_count'] * 100) / total
        values = {
            'team': team,
            'ratings': ratings,
            'stats': stats,
        }
        return request.render('website_helpdesk_rating.team_rating_page', values)
