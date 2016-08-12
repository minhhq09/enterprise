# -*- coding: utf-8 -*-
from openerp import models, fields, api


class GcmResConfig(models.TransientModel):
    _inherit = 'base.config.settings'

    gcm_api_key = fields.Char('Server API Key')
    gcm_project_id = fields.Char('Sender ID')

    @api.multi
    def set_gcm_api_key(self):
        gcm_api_key = self[0].gcm_api_key or ''
        self.env['ir.config_parameter'].set_param('gcm_api_key', gcm_api_key)

    @api.multi
    def set_gcm_project_id(self):
        gcm_project_id = self[0].gcm_project_id or ''
        self.env['ir.config_parameter'].set_param('gcm_project_id', gcm_project_id)

    @api.multi
    def get_default_gcm_credentials(self, fields):
        get_param = self.env['ir.config_parameter'].get_param
        gcm_api_key = get_param('gcm_api_key', default='')
        gcm_project_id = get_param('gcm_project_id', default='')
        return {
            'gcm_api_key': gcm_api_key,
            'gcm_project_id': gcm_project_id
        }
