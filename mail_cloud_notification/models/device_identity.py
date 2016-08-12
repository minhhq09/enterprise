# -*- coding: utf-8 -*-
from openerp import models, fields, api


class DeviceIdentity(models.Model):
    _name = 'device.identity'

    @api.model
    def _default_service_type(self):
        return []

    name = fields.Char(string="Device Name")
    partner_id = fields.Many2one('res.partner', 'Partner')
    subscription_id = fields.Char('Subscription ID', groups='base.group_system')
    service_type = fields.Selection('_default_service_type', 'Notification Service')

    @api.model
    def create(self, values):
        identity = super(DeviceIdentity, self).create(values)
        body = "<strong>%s</strong> device registered for Mobile notifications" % (identity.name)
        identity.partner_id.message_post(body=body, subtype="mail.mt_comment")
        return identity

    @api.multi
    def unlink(self):
        for device_identity in self:
            body = "<strong>%s</strong> device removed for Mobile notifications" % (device_identity.name)
            device_identity.partner_id.message_post(body=body, subtype="mail.mt_comment")
        return super(DeviceIdentity, self).unlink()
