# -*- coding: utf-8 -*-
import requests
import simplejson
import datetime
import time

from openerp import models, api, fields
from openerp.exceptions import UserError
from openerp.tools.translate import _

class OnlineInstitution(models.Model):
    _inherit = 'online.institution'

    type = fields.Selection(selection_add=[('yodlee', 'Yodlee')])

class OnlineSyncConfig(models.TransientModel):
    _inherit = 'account.journal.onlinesync.config'

    yodlee_account_id = fields.Many2one('online.account', related='online_account_id', readonly=True)

class YodleeAccountJournal(models.Model):
    _inherit = 'account.journal'
    '''
    online_account save the yodlee account on the journal.
    This yodlee.account record fetchs the bank statements
    '''

    def _get_yodlee_credentials(self):
        ICP_obj = self.env['ir.config_parameter']
        login = ICP_obj.get_param('yodlee_id')
        secret = ICP_obj.get_param('yodlee_secret')
        url = ICP_obj.get_param('yodlee_service_url')
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
        resp_json = simplejson.loads(self.fetch('/jsonsdk/SiteTraversal/getAllSites', 'yodlee', {}))
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
            resp = requests.post(credentials['url']+'/authenticate/coblogin', params=login, timeout=3)
        except Exception:
            raise UserError(_('An error has occurred while trying to connect to yodlee service'))
        resp_json = simplejson.loads(resp.text)
        if 'cobrandConversationCredentials' not in resp_json:
            raise UserError(_('Incorrect Yodlee login/password, please check your credentials in accounting/settings'))
        self.company_id.write({'yodlee_access_token': resp_json['cobrandConversationCredentials']['sessionToken'],
                'yodlee_last_login': datetime.datetime.now(),})

    @api.multi
    def _get_user_access(self):
        # This method log in yodlee user
        # This method is used by fetch()
        credentials = self._get_yodlee_credentials()
        params = {
            'cobSessionToken': self.company_id.yodlee_access_token,
            'login': self.company_id.yodlee_user_login,
            'password': self.company_id.yodlee_user_password,
        }
        try:
            resp = requests.post(credentials['url']+'/authenticate/login', params=params, timeout=3)
        except Exception:
            raise UserError(_('An error has occurred while trying to connect to yodlee service'))
        resp_json = simplejson.loads(resp.text)
        if not resp_json.get('userContext', False):
            raise UserError(resp_json.get('Error', False) and resp_json['Error'][0].get('errorDetail', 'Error') or 'An Error has occurred')
        self.company_id.write({'yodlee_user_access_token': resp_json['userContext']['conversationCredentials']['sessionToken'],
                'yodlee_user_last_login': datetime.datetime.now(),})

    @api.multi
    def fetch(self, service, online_type, params, type_request='post'):
        if online_type != 'yodlee':
            return super(YodleeAccountJournal, self).fetch(service, online_type, params, type_request=type_request)

        credentials = self._get_yodlee_credentials()
        last_login = self.company_id.yodlee_last_login and datetime.datetime.strptime(self.company_id.yodlee_last_login, "%Y-%m-%d %H:%M:%S")
        delta = last_login and (datetime.datetime.now() - last_login).seconds or 101 * 60
        if not self.company_id.yodlee_access_token or delta / 60 >= 95:
            self._get_access_token()
        user_last_date = self.company_id.yodlee_user_last_login and datetime.datetime.strptime(self.company_id.yodlee_user_last_login, "%Y-%m-%d %H:%M:%S")
        delta = self.company_id.yodlee_user_last_login and (datetime.datetime.now() - user_last_date).seconds or 31 * 60
        if not self.company_id.yodlee_user_access_token or delta / 60 >= 25:
            self._get_user_access()
        params['cobSessionToken'] = self.company_id.yodlee_access_token
        params['userSessionToken'] = self.company_id.yodlee_user_access_token
        try:
            resp = requests.post(credentials['url'] + service, params=params, timeout=3)
        except Exception:
            raise UserError(_('An error has occurred while trying to connect to yodlee service'))
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

    site_account_id = fields.Char("Site id")
    account_id = fields.Char("Account id")

    @api.multi
    def yodlee_refresh(self, depth=30):
        # Ask yodlee to refresh the account
        if depth <= 0:
            return False
        time.sleep(2)
        # yodlee = self.env.user.get_yodlee()
        yodlee = self.journal_id
        params = {
            'memSiteAccId': self.site_account_id,
        }
        resp_json = simplejson.loads(yodlee.fetch('/jsonsdk/Refresh/getSiteRefreshInfo', 'yodlee', params))
        if resp_json['code'] == 801:
            return self.yodlee_refresh(depth - 1)
        elif resp_json['code'] == 0 and resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_COMPLETED' and \
             resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_TIMED_OUT' and \
             resp_json['siteRefreshStatus']['siteRefreshStatus'] != 'REFRESH_COMPLETED_ACCOUNTS_ALREADY_AGGREGATED':
            return self.yodlee_refresh(depth - 1)
        elif resp_json['code'] == 0:
            return True
        else:
            return False

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
        from_date = datetime.datetime.strptime(self.last_sync, "%Y-%m-%d")
        from_date = datetime.datetime.strftime(from_date, "%m-%d-%Y")
        params = {
            'transactionSearchRequest.containerType': 'All',
            'transactionSearchRequest.higherFetchLimit': 500,
            'transactionSearchRequest.lowerFetchLimit': 1,
            'transactionSearchRequest.resultRange.endNumber': 100,
            'transactionSearchRequest.resultRange.startNumber': 1,
            'transactionSearchRequest.searchClients.clientId': 1,
            'transactionSearchRequest.searchClients.clientName': 'DataSearchService',
            'transactionSearchRequest.userInput': '',
            'transactionSearchRequest.ignoreUserInput': True,
            'transactionSearchRequest.searchFilter.postDateRange.fromDate': from_date,
            'transactionSearchRequest.searchFilter.transactionSplitType': 'ALL_TRANSACTION',
            'transactionSearchRequest.searchFilter.itemAccountId.identifier': self.account_id,
        }
        resp_json = simplejson.loads(self.journal_id.fetch('/jsonsdk/TransactionSearchService/executeUserSearchRequest', 'yodlee', params))
        # Prepare the transaction
        if resp_json.get('numberOfHits', 0) > 0:
            transactions = []
            for transaction in resp_json['searchResult']['transactions']:
                transaction_date = transaction.get('transactionDate').split("T")[0]
                if transaction.get('transactionBaseType') == 'debit':
                    amount = transaction['amount']['amount']
                else:
                    amount = -1 * transaction['amount']['amount']
                transactions.append({
                    'id': transaction['viewKey']['transactionId'],
                    'date': transaction_date,
                    'description': transaction['description']['description'],
                    'amount': amount,
                    'end_amount': transaction['account']['accountBalance']['amount'],
                })

            return self.env['account.bank.statement'].online_sync_bank_statement(transactions, self.journal_id)
        return action
