# -*- coding: utf-8 -*-
from openerp import models


class CloudMessageDispatch(models.AbstractModel):
    """ AbstractModel for cloud messaging

        To use this create def send_<cloud messaging type>

        e.g for google cloud messaging(gcm) create method like
        def send_gcm(identities, message)

        :param identities: list of device to send message
        :param message: which message to send

    """
    _name = 'cloud.message.dispatch'
