# -*- coding: utf-8 -*-
import math
import requests
import json
import datetime
import time
import logging
import uuid

from openerp import models, api, fields
from openerp.exceptions import UserError
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)

class OnlineInstitution(models.Model):
    _inherit = 'online.institution'

    type = fields.Selection(selection_add=[('yodlee', 'Yodlee')])

    @api.multi
    def _migrate_online_institution(self):
        self.env['ir.model.data'].search([('module', '=', 'account_yodlee'), ('model', '=', 'online.institution')]).unlink()

class OnlineSyncConfig(models.TransientModel):
    _inherit = 'account.journal.onlinesync.config'

    yodlee_account_id = fields.Many2one('online.account', related='online_account_id', readonly=True)

class YodleeAccountJournal(models.Model):
    _inherit = 'account.journal'
    '''
    online_account save the yodlee account on the journal.
    This yodlee.account record fetchs the bank statements
    '''

    def _raise_exception(self, e, resp):
        msg = ''
        if isinstance(e, requests.HTTPError):
            msg = " (%s)" % (e.response.status_code)
        _logger.exception('An error has occurred while trying to connect to yodlee service')
        raise UserError(_('An error has occurred while trying to connect to yodlee service') + msg)

    @api.multi
    def remove_online_account(self):
        if self.online_type == 'yodlee' and self.online_account_id.site_account_id:
            # Call yodlee API to delete account
            params = {'memSiteAccId': self.online_account_id.site_account_id}
            resp_json = json.loads(self.fetch('/jsonsdk/SiteAccountManagement/removeSiteAccount', 'yodlee', params))
            if resp_json.get('errorOccurred') and resp_json.get('exceptionType') != 'com.yodlee.core.InvalidSiteAccountException':
                raise UserError(_('An error has occured while trying to remove/update account.\nMessage: %s') % (resp_json.get('message', 'Error')))
        return super(YodleeAccountJournal, self).remove_online_account()

    @api.multi
    def save_online_account(self, vals, online_institution_id):
        # If we have the same site_account_id, it means that user has just reconfigured it's account, so
        # do not remove SiteAccount from yodlee server.
        if self.online_account_id and self.online_account_id.site_account_id == str(vals.get('site_account_id')):
            self.online_account_id.write(vals)
            return self.online_account_id.online_sync()
        else:
            super(YodleeAccountJournal, self).save_online_account(vals, online_institution_id)

    @api.multi
    def launch_wizard(self):
        if self.online_institution_id.type == 'yodlee':
            return {
                'type': 'ir.actions.client',
                'tag': 'yodlee_online_sync_widget',
                'target': 'new',
                'context': {'journal_id': self.id, 
                            'online_id': self.online_id,
                            'online_institution_id': self.online_institution_id.id, 
                            },
            }
        else:
            return super(YodleeAccountJournal, self).launch_wizard()

    @api.multi
    def online_sync(self):
        if not self.online_account_id:
            raise UserError(_('You must first link your bank account to this journal before attempting a refresh'))
        
        if self.online_institution_id.type != 'yodlee':
            return super(YodleeAccountJournal, self).online_sync()

        params = {
            'memSiteAccId': self.online_account_id.site_account_id,
            'refreshParameters.refreshPriority': 1,
        }
        resp_json = json.loads(self.fetch('/jsonsdk/Refresh/startSiteRefresh', 'yodlee', params))
        if resp_json.get('errorCode'):
            raise UserError(_('An error has occured while trying to refresh the site.\nError code: %s\nError message: %s')\
                % (resp_json.get('errorCode'), resp_json.get('errorDetail')))
        if not resp_json.get('siteRefreshStatus', False) or resp_json.get('errorOccurred', False):
            raise UserError(_('An error has occured while trying to refresh the site.\nMessage: %s') % (resp_json.get('message', 'Error')))
        if resp_json['siteRefreshStatus']['siteRefreshStatus'] == 'REFRESH_TRIGGERED':
            if resp_json['siteRefreshMode']['refreshMode'] == 'MFA':
                # open widget at second step
                action = self.launch_wizard()
                action['context'].update({'step': 'mfa', 'site_account_id': self.online_account_id.site_account_id})
                return action
            else:
                #perform sync
                return self.online_account_id.online_sync()
        elif resp_json['siteRefreshStatus']['siteRefreshStatus'] == 'SITE_CANNOT_BE_REFRESHED':
            raise UserError(_('Please execute manual synchronization every few minutes'))
        elif resp_json['siteRefreshStatus']['siteRefreshStatus'] == 'REFRESH_ALREADY_IN_PROGRESS':
            # Refresh had already been triggered so perform a refresh
            return self.online_account_id.online_sync()
        else:
            raise UserError(_('Incorrect Refresh status received: %s (expected REFRESH_TRIGGERED)') % (resp_json['siteRefreshStatus']['siteRefreshStatus']))

    @api.multi
    def online_sync_refresh(self):
        return self.online_account_id.online_sync()

    @api.one
    def _register_new_yodlee_user(self):
        username = self.env.registry.db_name + '_' + str(uuid.uuid4())
        password = str(uuid.uuid4())
        email = self.company_id.partner_id.email
        if not email:
            raise UserError(_('Please configure an email in the company settings.'))
        
        credentials = self._get_yodlee_credentials()
        url = credentials['url']
        try:
            params = {
                'cobSessionToken': self.company_id.yodlee_access_token,
                'userCredentials.loginName': username,
                'userCredentials.password': password,
                'userCredentials.objectInstanceType': 'com.yodlee.ext.login.PasswordCredentials',
                'userProfile.emailAddress': email
            }
            resp = requests.post(url + '/jsonsdk/UserRegistration/register3', params=params, timeout=20)
            resp_json = json.loads(resp.text)
            if resp_json.get('errorOccurred', False) == 'true':
                #Log error if any
                errorMsg = _('An error occured while trying to register new user on yodlee: ') + resp_json.get('exceptionType', 'Unknown Error') + ' - Message: ' +resp_json.get('message', '')
                raise UserError(errorMsg)
            else:
                return self.company_id.write({'yodlee_user_login': username, 'yodlee_user_password': password,})
            resp.raise_for_status()
        except Exception as e:
            self._raise_exception(e, resp)

    @api.model
    def _get_yodlee_credentials(self):
        ICP_obj = self.env['ir.config_parameter'].sudo()
        login = ICP_obj.get_param('yodlee_id') or self._cr.dbname
        secret = ICP_obj.get_param('yodlee_secret') or ICP_obj.get_param('database.uuid')
        url = ICP_obj.get_param('yodlee_service_url') or 'https://onlinesync.odoo.com/yodlee/api'
        return {'login': login, 'secret': secret, 'url': url,}

    @api.multi
    def fetch_all_institution(self):
        # If nothing is configured, do not try to synchronize (cron job)
        credentials = self._get_yodlee_credentials()
        if not credentials['url'] \
            or not credentials['login'] \
            or not credentials['secret'] \
            or not self.company_id.yodlee_user_login \
            or not self.company_id.yodlee_user_password:
            return super(YodleeAccountJournal, self).fetch_all_institution()
        resp_json = json.loads(self.fetch('/jsonsdk/SiteTraversal/getAllSites', 'yodlee', {}))
        institutions = self.env['online.institution'].search([('type', '=', 'yodlee')])
        institution_name = [i.name for i in institutions]
        for institution in resp_json:
            if institution['defaultDisplayName'] not in institution_name:
                self.env['online.institution'].create({
                    'name': institution['defaultDisplayName'],
                    'online_id': institution['siteId'],
                    'type': 'yodlee',
                })
        return super(YodleeAccountJournal, self).fetch_all_institution()

    @api.multi
    def _get_access_token(self):
        # Need a new access_token
        # This method is used by fetch()
        credentials = self._get_yodlee_credentials()
        if not credentials['login'] or not credentials['secret'] or not credentials['url']:
            raise UserError(_('Please configure your yodlee account first in accounting>settings'))
        login = {
            'cobrandLogin': credentials['login'],
            'cobrandPassword': credentials['secret'],
        }
        try:
            resp = requests.post(credentials['url']+'/authenticate/coblogin', params=login, timeout=20)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (400, 403):
                raise UserError(_('An error has occurred while trying to connect to Yodlee service ') + e.response.content)
            else:
                raise UserError(_('An error has occurred while trying to connect to Yodlee service ') + str(e.response.status_code))
        except Exception as e:
            self._raise_exception(e, resp)
        resp_json = json.loads(resp.text)
        if 'error' in resp_json:
            raise UserError(resp_json.get('error'))
        if 'cobrandConversationCredentials' not in resp_json:
            raise UserError(_('Incorrect Yodlee login/password, please check your credentials in accounting/settings'))
        self.company_id.write({'yodlee_access_token': resp_json['cobrandConversationCredentials']['sessionToken'],
                'yodlee_last_login': datetime.datetime.now(),})

    @api.multi
    def _get_user_access(self):
        # This method log in yodlee user
        # This method is used by fetch()
        credentials = self._get_yodlee_credentials()
        if not self.company_id.yodlee_user_login:
            self._register_new_yodlee_user()
        params = {
            'cobSessionToken': self.company_id.yodlee_access_token,
            'login': self.company_id.yodlee_user_login,
            'password': self.company_id.yodlee_user_password,
        }
        try:
            resp = requests.post(credentials['url']+'/authenticate/login', params=params, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            self._raise_exception(e, resp)
        resp_json = json.loads(resp.text)
        if not resp_json.get('userContext', False):
            raise UserError(resp_json.get('Error', False) and resp_json['Error'][0].get('errorDetail', 'Error') or _('An Error has occurred'))
        self.company_id.write({'yodlee_user_access_token': resp_json['userContext']['conversationCredentials']['sessionToken'],
                'yodlee_user_last_login': datetime.datetime.now(),})

    @api.multi
    def fetch(self, service, online_type, params, type_request='post'):
        if online_type != 'yodlee':
            return super(YodleeAccountJournal, self).fetch(service, online_type, params, type_request=type_request)
        credentials = self._get_yodlee_credentials()
        last_login = self.company_id.yodlee_last_login and datetime.datetime.strptime(self.company_id.yodlee_last_login, "%Y-%m-%d %H:%M:%S")
        delta = last_login and (datetime.datetime.now() - last_login).total_seconds() or 101 * 60
        if not self.company_id.yodlee_access_token or delta / 60 >= 95:
            self._get_access_token()
        user_last_date = self.company_id.yodlee_user_last_login and datetime.datetime.strptime(self.company_id.yodlee_user_last_login, "%Y-%m-%d %H:%M:%S")
        delta = self.company_id.yodlee_user_last_login and (datetime.datetime.now() - user_last_date).total_seconds() or 31 * 60
        if not self.company_id.yodlee_user_access_token or delta / 60 >= 25:
            self._get_user_access()
        params['cobSessionToken'] = self.company_id.yodlee_access_token
        params['userSessionToken'] = self.company_id.yodlee_user_access_token
        try:
            resp = requests.post(credentials['url'] + service, params=params)
            _logger.info('Yodlee call to %s with params %s' % (service, params))
            resp.raise_for_status()
        except Exception as e:
            self._raise_exception(e, resp)
        _logger.info('Yodlee response to %s: %s' % (service, resp.json()))
        return resp.text


class ResCompany(models.Model):
    _inherit = 'res.company'

    yodlee_last_login = fields.Datetime("Last login")
    yodlee_access_token = fields.Char("access_token")
    yodlee_user_login = fields.Char("Yodlee login")
    yodlee_user_password = fields.Char("Yodlee password")
    yodlee_user_access_token = fields.Char("Yodlee access token")
    yodlee_user_last_login = fields.Datetime("last login")


class YodleeAccount(models.Model):
    _inherit = 'online.account'
    '''
    The yodlee account that is saved in Odoo.
    It knows how to fetch Yodlee to get the new bank statements
    '''

    site_account_id = fields.Char("Site")
    account_id = fields.Char("Account")

    @api.multi
    def yodlee_refresh(self, depth=90):
        # Ask yodlee to refresh the account
        if depth <= 0:
            return False
        time.sleep(2)
        yodlee = self.journal_id
        params = {
            'memSiteAccId': self.site_account_id,
        }
        resp_json = json.loads(yodlee.fetch('/jsonsdk/Refresh/getSiteRefreshInfo', 'yodlee', params))
        if resp_json.get('errorCode'):
            raise UserError(
                _('An error has occured while trying to get transactions, try again later.\nError code: %s\nError message: %s')\
                % (resp_json.get('errorCode'), resp_json.get('errorDetail'))
            )
        if resp_json['code'] == 801:
            if depth == 1:
                _logger.warning('Max depth reached when trying to refresh account site, last json is: %s' % (resp_json))
            return self.yodlee_refresh(depth - 1)
        elif resp_json['code'] == 0 and resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_COMPLETED' and \
             resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_TIMED_OUT' and \
             resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_COMPLETED_ACCOUNTS_ALREADY_AGGREGATED' and \
             resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_COMPLETED_WITH_UNCERTAIN_ACCOUNT':
            if depth == 1:
                _logger.warning('Max depth reached when trying to refresh account site, last json is: %s' % (resp_json))
            return self.yodlee_refresh(depth - 1)
        elif resp_json['code'] == 0:
            return True
        else:
            _logger.warning('A problem occurred while refreshing account site, json is: %s' % (resp_json))
            return False

    def get_transactions(self, resp_json):
        transactions = []
        if resp_json.get('numberOfHits', 0) > 0:
            if type(resp_json['searchResult']['transactions']) != list:
                _logger.warning('A problem getting back transactions for yodlee has occurred, json is: %s' % (resp_json))
            for transaction in resp_json['searchResult']['transactions']:
                tr_date = transaction.get('postDate', transaction.get('transactionDate', fields.Date.today()))
                transaction_date = datetime.datetime.strptime(tr_date.split("T")[0], '%Y-%m-%d')
                if transaction.get('transactionBaseType') == 'debit':
                    amount = -1 * transaction['amount']['amount']
                else:
                    amount = transaction['amount']['amount']
                if amount == 0:
                    continue
                transactions.append({
                    'id': transaction['viewKey']['transactionId'],
                    'date': datetime.datetime.strftime(transaction_date, DEFAULT_SERVER_DATE_FORMAT),
                    'description': transaction['description']['description'],
                    'amount': amount,
                    'end_amount': transaction['account']['accountBalance']['amount'],
                })
        return transactions

    @api.multi
    def online_sync(self):
        if (self.institution_id.type != 'yodlee'):
            return super(YodleeAccount, self).online_sync()

        action_rec = self.env['ir.model.data'].xmlid_to_object('account.open_account_journal_dashboard_kanban')
        if action_rec:
            action = action_rec.read([])[0]
        # Get the new transactions and returns a list of transactions (they are managed in account_online_sync)
        # 1) Refresh
        if not self.yodlee_refresh():
            raise UserError(_('An error has occured while trying to get transactions, try again later'))
        # 2) Fetch
        # Convert the date at the correct format
        from_date = datetime.datetime.strptime(self.last_sync, DEFAULT_SERVER_DATE_FORMAT)
        from_date = datetime.datetime.strftime(from_date, "%m-%d-%Y")
        to_date = datetime.datetime.strptime(fields.Date.today(), DEFAULT_SERVER_DATE_FORMAT)
        to_date = datetime.datetime.strftime(to_date, "%m-%d-%Y")
        params = {
            'transactionSearchRequest.containerType': 'All',
            'transactionSearchRequest.higherFetchLimit': 500,
            'transactionSearchRequest.lowerFetchLimit': 1,
            'transactionSearchRequest.resultRange.endNumber': 500,
            'transactionSearchRequest.resultRange.startNumber': 1,
            'transactionSearchRequest.searchClients.clientId': 1,
            'transactionSearchRequest.searchClients.clientName': 'DataSearchService',
            'transactionSearchRequest.userInput': '',
            'transactionSearchRequest.ignoreUserInput': True,
            'transactionSearchRequest.searchFilter.postDateRange.fromDate': from_date,
            'transactionSearchRequest.searchFilter.postDateRange.toDate': to_date,
            'transactionSearchRequest.searchFilter.transactionSplitType': 'ALL_TRANSACTION',
            'transactionSearchRequest.searchFilter.transactionStatus.description': 'posted',
            'transactionSearchRequest.searchFilter.transactionStatus.statusId': 1,
            'transactionSearchRequest.searchFilter.itemAccountId.identifier': self.account_id,
            # 'transactionSearchRequest.searchFilter.setFirstCall': True,
        }
        resp_json = json.loads(self.journal_id.fetch('/jsonsdk/TransactionSearchService/executeUserSearchRequest', 'yodlee', params))
        # get the transactions
        transactions = self.get_transactions(resp_json)
        # If we have more than 500 transactions, keep requesting yodlee for the next transactions (by batch of 500)
        # see: https://developer.yodlee.com/Knowledge_Base/Transactions
        perform_call = math.ceil(resp_json.get('countOfAllTransaction', 0)/500.0) - 1
        while perform_call > 0:
            params['transactionSearchRequest.searchFilter.setFirstCall'] = False
            params['transactionSearchRequest.resultRange.startNumber'] += 500
            params['transactionSearchRequest.resultRange.endNumber'] += 500
            params['transactionSearchRequest.lowerFetchLimit'] += 500
            params['transactionSearchRequest.higherFetchLimit'] += 500
            resp_json = json.loads(self.journal_id.fetch('/jsonsdk/TransactionSearchService/executeUserSearchRequest', 'yodlee', params))
            transactions.extend(self.get_transactions(resp_json))
            perform_call -= 1

        if len(transactions) > 0:
            return self.env['account.bank.statement'].online_sync_bank_statement(transactions, self.journal_id)
        return action
