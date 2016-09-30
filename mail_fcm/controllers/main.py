# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request


class WebFcm(http.Controller):

    @http.route('/get_fcm_info', type='json', auth="user")
    def get_session_info(self):
        return {
            'subscription_ids': request.env.user.partner_id.device_identity_ids.mapped('subscription_id'),
            'fcm_project_id': request.env['cloud.message.dispatch']._get_default_fcm_credentials()["fcm_project_id"],
            'partner_id': request.env.user.partner_id.id,
            'inbox_action': request.env.ref('mail.mail_channel_action_client_chat').id
        }
