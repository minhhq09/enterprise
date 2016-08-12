# -*- coding: utf-8 -*-
import logging
import re
import threading

from gcm import GCM
from gcm.gcm import GCMAuthenticationException, GCMUnavailableException
from requests.exceptions import ConnectionError

from openerp import models, api
from openerp.modules.registry import Registry
from openerp.addons.mail.models.html2text import html2text

GCM_MESSAGES_LIMIT = 1000
_logger = logging.getLogger(__name__)


class CloudMessageDispatch(models.AbstractModel):
    _inherit = 'cloud.message.dispatch'

    @api.model
    def send_gcm(self, identities, message):
        # Divided into chunks because GCM supports only 1000 users in multi-cast
        message.ensure_one()
        identities_chunks = [identities[i:i+GCM_MESSAGES_LIMIT] for i in xrange(0, len(identities), GCM_MESSAGES_LIMIT)]
        payload = self.prepare_gcm_payload(message)
        for identities in identities_chunks:
            subscription_ids = identities.mapped('subscription_id')
            gcm_api_key = self.env['ir.config_parameter'].get_param('gcm_api_key')
            threaded_sending = threading.Thread(target=self._send_gcm_notification, args=(
                subscription_ids,
                payload,
                self.env.cr.dbname,
                self.env.uid,
                gcm_api_key
            ))
            threaded_sending.start()

    def _send_gcm_notification(self, subscription_ids, payload, dbname, uid, gcm_api_key):
        res = None
        if not gcm_api_key:
            _logger.exception("You need a GCM API key to run the GCM queue cron")
            return

        gcm = GCM(gcm_api_key)

        res = {}
        try:
            res = gcm.json_request(
                registration_ids=subscription_ids,
                data=payload
            )
        except GCMAuthenticationException:
            _logger.error("GCM Authentication: Provide valid GCM api key")
        except GCMUnavailableException:
            _logger.error("GCM service not available try after some time")
        except ConnectionError:
            _logger.error("No internet connection")
        except Exception:
            _logger.exception("Failed processing GCM queue")

        if 'errors' in res or 'canonical' in res:
            with api.Environment.manage():
                with Registry(dbname).cursor() as cr:
                    env = api.Environment(cr, uid, {})
                    if 'errors' in res:
                        self.process_errors(res['errors'], env)
                    if 'canonical' in res:
                        self.process_canonical(res['canonical'], env)

    @api.model
    def prepare_gcm_payload(self, message):
        """Returns dictionary containing message information for mobile device. This info will be delivered
        to mobile device via Google Cloud Messaging(GCM). And it is having limit of 4000 bytes (4kb)
        """
        payload = {
            "author_name": message.author_id.name,
            "model": message.model,
            "res_id": message.res_id,
            "db_id": self.env['ir.config_parameter'].get_param('database.uuid')
        }
        if message.model == 'mail.channel':
            channel = message.channel_ids.filtered(lambda r: r.id == message.res_id)
            if channel.channel_type == 'chat':
                payload['subject'] = message.author_id.name
                payload['type'] = 'chat'
            else:
                payload['subject'] = "#%s" % (message.record_name)
        else:
            payload['subject'] = message.record_name or message.subject
        payload_length = len(str(payload).encode("utf-8"))
        if payload_length < 4000:
            body = re.sub(ur'<a(.*?)>', r'<a>', message.body)  # To-Do : Replace this fix
            payload['body'] = html2text(body)[:4000-payload_length]
        return payload

    @api.model
    def process_errors(self, errors, env):
        """We will delete wrong/unregistered subscription tokens.
        This function will handle following errors. Other errors like
        Authentication,Unavailable will be handled by GCM library it self
            > InvalidRegistration: Due to wrong subscription token
            > MismatchSenderId: Sent through wrong sender probably due to change in api key
            > NotRegistered: Subscription token unregistered from device
        """
        invalid_subscriptions = []
        for e in ["InvalidRegistration", "MismatchSenderId", "NotRegistered"]:
            invalid_subscriptions += errors.get(e, [])
        subscription_to_remove = env['device.identity'].search([('subscription_id', 'in', invalid_subscriptions)])
        subscription_to_remove.unlink()

    @api.model
    def process_canonical(self, canonical, env):
        """ If user have multiple registrations for the same device and you try to send
        a message using an old registration token, GCM will process the request as usual,
        but it includes the canonical ID in the response. We will delete/replace such token.
        Response Format: {'new_token': 'old_token'}
        """
        all_subsciptions = canonical.keys() + canonical.values()
        subscription_exists = env['device.identity'].search(['subscription_id', 'in', all_subsciptions])
        token_exists = subscription_exists.mapped["subscription_id"]
        for new, old in canonical.items():
            if old in token_exists and new in token_exists:
                subscription_exists.filtered(lambda r: r.subscription_id == old).unlink()
            elif old in token_exists and new not in token_exists:
                subscription_exists.filtered(lambda r: r.subscription_id == old).write({'subscription_id': new})
