# -*- coding: utf-8 -*-
import requests
import simplejson
import datetime

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class PlaidAccountJournal(models.Model):
    _inherit = 'account.journal'

    online_account = fields.Reference(selection_add=[('plaid.account', 'plaid')])

class PlaidInstitutionTransient(models.TransientModel):
    """
    This wizard let the user fill the information needed
    to connect to an institution
    """
    _name = 'plaid.institution.transient'

    configured = fields.Boolean("Plaid well configured")
    
    type = fields.Char("Type", required=1)
    name = fields.Char("name", required=1)
    error = fields.Char("Error")
    wizard_id = fields.Many2one('online.synch.wizard')

    have_username = fields.Boolean(string="Have Username")
    have_passwd = fields.Boolean(string="Have Password")
    have_pin = fields.Boolean(string="Have Pin")
    mfa_code = fields.Boolean("Have MFA code")
    plaid_id = fields.Char("Plaid ID", required=1)

    username = fields.Char(string="Username")
    passwd = fields.Char(string="Password")
    pin = fields.Char(string="Pin")

    @api.model
    def create_wizard(self, institution):
        configured = self.env['plaid.credentials'].is_configured()
        wizard = self.create({
            'type': institution['type'],
            'name': institution['name'],
            'have_username': institution['have_username'],
            'have_passwd': institution['have_passwd'],
            'have_pin': institution['have_pin'],
            'mfa_code': institution['mfa_code'],
            'plaid_id': institution['plaid_id'],
            'configured': configured,
        })
        return wizard.launch_wizard()

    @api.model
    def create_wizard_from_id(self, institution_id):
        resp = requests.get('https://api.plaid.com/institutions/' + institution_id)
        institution = simplejson.loads(resp.text)
        configured = self.env['plaid.credentials'].is_configured()
        wizard = self.create({
            'type': institution['type'],
            'name': institution['name'],
            'have_username': 'username' in institution['credentials'],
            'have_passwd': 'password' in institution['credentials'],
            'have_pin': 'pin' in institution['credentials'],
            'mfa_code': 'code' in institution['mfa'],
            'plaid_id': institution['id'],
            'configured': configured,
        })
        return wizard.with_context(goal='login').launch_wizard()
        
    @api.multi
    def launch_wizard(self):
        return {
            'name': _('Log in'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plaid.institution.transient',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    @api.multi
    def plaid_login(self):
        return self.env['plaid.mfa.response.wizard'].create_wizard_with_institution(institution=self)

class PaidInstitution(models.Model):
    """
    Is used to saved the institution of a online.account
    Useful when updating the credentials of the user
    """
    _name = 'plaid.institution'

    type = fields.Char("Type", required=1)
    name = fields.Char("name", required=1)

    have_username = fields.Boolean(string="Have Username")
    have_passwd = fields.Boolean(string="Have Password")
    have_pin = fields.Boolean(string="Have Pin")
    mfa_code = fields.Boolean("Have MFA code")
    plaid_id = fields.Char("Plaid ID", required=1)

class PlaidMfaResponseWizard(models.TransientModel):
    """
    The user complete the MFA in this wizard
    """
    _name = 'plaid.mfa.response.wizard'

    mfa_type = fields.Selection([('message', 'message'),
                                 ('selections', 'selections'),
                                 ('code', 'code')])
    message = fields.Char("Message")
    response = fields.Char("Response")
    selections = fields.Char("JSON in Char")
    access_token = fields.Char("Access Token")
    error = fields.Char("error")
    institution_wizard_id = fields.Many2one('plaid.institution.transient')
    code_wizard_id = fields.Many2one('plaid.code.wizard')

    @api.model
    def create_wizard_with_institution(self, institution=None, code=None):
        wizard = self.create({})
        if institution:
            wizard.institution_wizard_id = institution
        if code:
            wizard.code_wizard_id = code
            wizard.institution_wizard_id = code.institution_wizard_id
            return wizard.send_mfa()
        return wizard.create_wizard()

    @api.multi
    def create_wizard(self):
        # This method initialize the wizard, by fetching the MFA from Plaid.com
        plaid = self.env['plaid.credentials']

        # It the first time the user try to connect
        params = {
            'username': self.institution_wizard_id.username,
            'password': self.institution_wizard_id.passwd,
            'options': '{"login_only": true}'
        }
        if self.institution_wizard_id.pin:
            params['pin'] = self.institution_wizard_id.pin
        if self.institution_wizard_id.mfa_code:
            params['options'] = '{"login_only": true, "list":true}'
        # Update the access_token
        if self.env.context['goal'] == 'update':
            journal = self.env['account.journal'].search([('id', '=', self.env.context['active_id'])])
            params['access_token'] = jounral.online_account.access_token
            resp, resp_json = plaid.fetch_plaid("connect", params, type="patch")
        # create a new access_token
        if self.env.context['goal'] == 'login':
            params['type'] = self.institution_wizard_id.type
            resp, resp_json = plaid.fetch_plaid("connect", params)

        return self.mfa(resp, resp_json)

    @api.multi
    def send_mfa(self):
        # Trigger when the user click on the button 'continue'.
        plaid = self.env['plaid.credentials']

        if (self.response or self.selections) and self.access_token:
            # The mfa is a question or a selection
            params = {
                'access_token': self.access_token,
                'mfa': self.response,
            }
            resp, resp_json = plaid.fetch_plaid("connect/step", params)
        elif self.code_wizard_id:
            # The mfa is a code
            params = {
                'access_token': self.code_wizard_id.access_token,
                'options': '{"send_method":{"mask": "' + self.code_wizard_id.type_id.name + '"}}',
            }
            resp, resp_json = plaid.fetch_plaid("connect/step", params)
        
        return self.mfa(resp, resp_json)

    @api.multi
    def mfa(self, resp, resp_json):
        """
        This method display the MFA received by Plaid.com
        It's call when the wizard is created or when the user click on continue
        """
        # The connection is ok : go to next step
        if resp.status_code == 200:
            if self.env.context['goal'] == 'update':
                return True
            return self.env['plaid.select.account.wizard'].create_wizard_with_accounts(resp_json['accounts'], resp_json['access_token'], self.institution_wizard_id)
        # There is a MFA request
        elif resp.status_code == 201:
            # Reset the variables of the wizard
            self.error = ""
            self.message = ""
            self.response = ""
            self.selections = ""
            self.access_token = resp_json['access_token']
            # Display the right questions
            if resp_json['type'] == 'questions':
                self.mfa_type = 'message'
                self.message = resp_json['mfa'][0]['question']
            elif resp_json['type'] == 'selections':
                self.mfa_type = 'selections'
                self.selections = resp.text
            elif resp_json['type'] == 'list':
                code_wizard = self.env['plaid.code.wizard'].create({})
                return code_wizard.create_wizard_with_institution(self.institution_wizard_id, resp, resp_json)
            else:
                # When a code is sent
                self.mfa_type = 'message'
                self.message = resp_json['mfa']['message']
            return {
                'name': _('Multiple factor Authentification'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'plaid.mfa.response.wizard',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': self.env.context,
            }
        # Error from the user
        elif resp.status_code >= 400 and resp.status_code < 500:
            if resp_json['code'] == 1203:
                self.error = resp_json['resolve']
                return {
                    'name': _('Multiple factor Authentification'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'plaid.mfa.response.wizard',
                    'res_id': self.id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': self.env.context,
                }
            else:
                self.institution_wizard_id.error = resp_json['resolve']
                return self.institution_wizard_id.launch_wizard()
        # Error from plaid.com
        else:
            self.institution_wizard_id.error = _("Problem with Plaid.com.")
            return self.institution_wizard_id.create_wizard()

class PlaidSelectAccountWizard(models.TransientModel):
    _name = 'plaid.select.account.wizard'

    first_synch = fields.Date("First date", default=lambda self: datetime.datetime.now() - datetime.timedelta(15))
    access_token = fields.Char("access token")
    account_id = fields.Many2one('plaid.account.transient', string="Account")

    @api.model
    def create_wizard_with_accounts(self, accounts, access_token, institution):
        wizard = self.create({})
        wizard.access_token = access_token
        for account in accounts:
            new_account = self.env['plaid.account.transient'].create({
                'name': account['meta']['name'],
                'plaid_id': account['_id'],
                'institution': institution.id,
                'balance_current': account['balance']['current'],
            })
            new_account['wizard_id'] = wizard
            if account['balance'].get('available'):
                new_account['balance_available'] = account['balance']['available']
        return wizard.create_wizard()

    @api.multi
    def create_wizard(self):
        return {
            'name': _('Select account'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plaid.select.account.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    @api.multi
    def select(self):
        inst = self.account_id['institution']
        journal = self.env['account.journal'].search([('id', '=', self.env.context['active_id'])])
        # Create a non transient model for the institution
        institution = self.env['plaid.institution'].create({
            'type': inst['type'],
            'name': inst['name'],
            'have_username': inst['have_username'],
            'have_passwd': inst['have_passwd'],
            'have_pin': inst['have_pin'],
            'mfa_code': inst['mfa_code'],
            'plaid_id': inst['plaid_id'],
        })
        # Create a non transient model for the account
        account = self.env['plaid.account'].create({
            'name': self.account_id['name'],
            'plaid_id': self.account_id['plaid_id'],
            'balance_available': self.account_id['balance_available'],
            'balance_current': self.account_id['balance_current'],
            'access_token': self.access_token,
            'journal_id': journal.id,
        })
        account.last_synch = self.first_synch
        account['institution'] = institution
        journal = self.env['account.journal'].search([('id', '=', self.env.context['active_id'])])
        journal.online_account = account
        # Run a first synchronization
        return account.online_synch()


class PlaidCodeWizard(models.TransientModel):
    _name = 'plaid.code.wizard'

    access_token = fields.Char("Access Token")
    institution_wizard_id = fields.Many2one('plaid.institution.transient', "Institution")
    type_id = fields.Many2one('plaid.code.selection', "Choice")

    @api.multi
    def create_wizard_with_institution(self, institution, resp, resp_json):
        self.institution_wizard_id = institution
        # IF GOOD
        if (resp.status_code == 201):
            for select in resp_json['mfa']:
                code = self.env['plaid.code.selection'].create({
                    'name': select['mask'],
                })
                code['wizard_id'] = self
            self.access_token = resp_json['access_token']
            return {
                'name': _('Select code'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'plaid.code.wizard',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': self.env.context,
            }
        elif (resp.status_code >= 400 and resp.status_code < 500):
            self.institution_wizard_id.error = resp_json['resolve']
            return self.institution_wizard_id.create_wizard()
        else:
            self.institution_wizard_id.error = _("Problem with Plaid.com. See mail for full log")
            return self.institution_wizard_id.create_wizard()

    @api.multi
    def select(self):
        return self.env['plaid.mfa.response.wizard'].create_wizard_with_institution(code=self)

class PlaidCodeSelection(models.TransientModel):
    _name = 'plaid.code.selection'

    name = fields.Char("Name", required=1)
    wizard_id = fields.Many2one('plaid.code.wizard', String="Wizard")

class PlaidAccountTransient(models.TransientModel):
    _name = 'plaid.account.transient'

    name = fields.Char("Name")
    plaid_id = fields.Char("Plaid Account")
    institution = fields.Many2one('plaid.institution.transient', String="Institution")
    balance_available = fields.Float("Available balance")
    balance_current = fields.Float("Current balance")
    access_token = fields.Char("Access token")
    wizard_id = fields.Many2one('plaid.select.account.wizard')


class PlaidAccount(models.Model):
    _name = 'plaid.account'
    _inherit = 'online.account'

    plaid_id = fields.Char("Plaid Account", required=1)
    institution = fields.Many2one('plaid.institution', String="Institution")
    balance_available = fields.Float("Available balance")
    balance_current = fields.Float("Current balance", required=1)
    access_token = fields.Char("Access Token", required=1)

    def online_synch(self):
        if self.last_synch > str(datetime.datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)):
            return
        # Fetch plaid.com
        # For all transactions since the last synchronization, for this journal
        params = {
            'access_token': self.access_token,
            'options': '{"gte": "' + self.last_synch + '", "account": "' + self.plaid_id + '"}',
        }
        plaid = self.env['plaid.credentials']
        resp, resp_json = plaid.fetch_plaid("connect/get", params)
        # Three possible cases : no error, user error, or plaid.com error
        # There is no error
        if resp.status_code == 200:
            # Update the balance
            for account in resp_json['accounts']:
                if account['_id'] == self.plaid_id:
                    end_amount = account['balance']['current']
            # Prepare the transaction
            transactions = []
            for transaction in resp_json['transactions']:
                trans = {
                    'id': transaction['_id'],
                    'date': datetime.datetime.strptime(transaction['date'], "%Y-%m-%d"),
                    'description': transaction['name'],
                    'amount': -1 * transaction['amount'],
                    'end_amount': end_amount,
                }
                if 'meta' in transaction and 'location' in transaction['meta']:
                    trans['location'] = transaction['meta']['location']
                transactions.append(trans)
            # Create the bank statement with the transactions
            return self.env['account.bank.statement'].online_synch_bank_statement(transactions, self.journal_id)
        # Error from the user (auth, ...)
        elif resp.status_code >= 400 and resp.status_code < 500:
            subject = _("Error in synchronization")
            body = _("The synchronization of the journal %s with the plaid account %s has failed.<br>"
                     "The error message is :<br>%s") % (self.name, self.plaid_id.name, resp_json['resolve'])
            self.plaid_id.message_post(body=body, subject=subject)
            return False
        # Error with Plaid.com
        else:
            subject = _("Error with Plaid.com")
            body = _("The synchronization with Plaid.com failed. Please check the error : <br> %s") % resp_json
            self.plaid_id.message_post(body=body, subject=subject)
            return False

    @api.multi
    def update_account(self):
        return self.env['plaid.institution.transient'].with_context(goal='update').create_wizard(self.institution)
        

class PlaidCredentials(models.Model):
    _name = 'plaid.credentials'

    @api.model
    def fetch_plaid(self, service, params, type="post"):
        params['client_id'] = self.env['ir.config_parameter'].get_param('plaid_id')
        params['secret'] = self.env['ir.config_parameter'].get_param('plaid_secret')
	if params['client_id'] == 'test_id' and params['secret'] == 'test_secret':
            # It's the credentials of the sandbox
            api = 'https://tartan.plaid.com/'
        else:
            api = 'https://api.plaid.com/'
        if type == "post":
            resp = requests.post(api + service, params=params)
        elif type == "patch":
            resp = requests.patch(api + service, params=params)
        return (resp, simplejson.loads(resp.text))

    @api.model
    def fetch_all_institution(self):
        self.env['online.institution'].search([('action_model', '=', 'plaid.institution.transient')]).unlink()
        resp = requests.get('https://api.plaid.com/institutions')
        for institution in simplejson.loads(resp.text):
            self.env['online.institution'].create({
                'name': institution['name'],
                'online_id': institution['id'],
                'sequence': 10,
                'action_model': 'plaid.institution.transient',
            })

    @api.model
    def is_configured(self):
        config = self.env['ir.config_parameter']
        return config.get_param('plaid_id') and config.get_param('plaid_secret')
        
