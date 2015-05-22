# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        vals = super(AccountJournal, self)._default_outbound_payment_methods()
        return vals + [(4, self.env.ref('account_sepa.account_payment_method_sepa_ct').id, None)]

    @api.model
    def _enable_sepa_ct_on_bank_journals(self):
        """ Enables sepa credit transfer payment method on bank journals. Called upon module installation via data file.
        """
        sepa_ct = self.env.ref('account_sepa.account_payment_method_sepa_ct')
        for bank_journal in self.search([('type', '=', 'bank')]):
            bank_journal.write({'outbound_payment_methods': [(4, sepa_ct.id, None)]})
