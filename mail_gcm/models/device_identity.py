# -*- coding: utf-8 -*-
from openerp import api, models


class DeviceIdentity(models.Model):
    _inherit = 'device.identity'

    @api.model
    def _default_service_type(self):
        selection = super(DeviceIdentity, self)._default_service_type()
        selection.append(('gcm', 'GCM'))
        return selection
