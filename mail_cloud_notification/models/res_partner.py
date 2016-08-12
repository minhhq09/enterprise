# -*- coding: utf-8 -*-
from openerp import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    device_identity_ids = fields.One2many(
        'device.identity', 'partner_id', string='Device identities', ondelete='cascade'
    )

    @api.multi
    def add_device_identity(self, subscription_id, device_name, service_type):
        """This method is going to use for adding new device subscription.

            :param  subscription_id : subscription_id or token from notification service
            :param  device_name: name of device e.g Nexus 5
        """
        device_identity_obj = self.env['device.identity'].sudo()
        for partner in self:
            subscription_exist = device_identity_obj.search([('subscription_id', '=', subscription_id)])
            if subscription_exist:
                subscription_exist.partner_id = partner.id
            else:
                device_identity_obj.create({'subscription_id': subscription_id, 'name': device_name, 'partner_id': partner.id, 'service_type': service_type})
