# -*- coding: utf-8 -*-

import openerp
from openerp import api, fields, models, _

class AccountConfigSettingsEnterpries(models.TransientModel):
    _inherit = 'account.config.settings'

    module_account_batch_deposit = fields.Boolean(string='Use batch deposit',
        help='This allows you to group received checks before you deposit them to the bank.\n'
             '-This installs the module account_batch_deposit.')
    module_account_sepa = fields.Boolean(string='Use sepa payment',
        help='If you check this box, you will be able to register your payment using SEPA.\n'
            '-This installs the module account_sepa.')
    module_account_plaid = fields.Boolean(string="Import of Bank Statements from Plaid.",
                                          help='Get your bank statements from you bank and import them through plaid.com.\n'
                                          '-that installs the module account_plaid.')
