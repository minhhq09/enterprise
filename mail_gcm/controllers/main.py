# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request


class WebGcm(http.Controller):

    @http.route('/get_gcm_info', type='json', auth="user")
    def get_session_info(self):
        return {
            'subscription_ids': request.env.user.partner_id.device_identity_ids.mapped('subscription_id'),
            'gcm_project_id': request.env['ir.config_parameter'].get_param('gcm_project_id'),
            'partner_id': request.env.user.partner_id.id,
            'inbox_action': request.env.ref('mail.mail_channel_action_client_chat').id
        }
