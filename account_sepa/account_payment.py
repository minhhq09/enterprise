# -*- coding: utf-8 -*-

import re

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from sepa_credit_transfer import check_valid_SEPA_str


class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.register.payments"

    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if hasattr(super(AccountRegisterPayments, self), '_onchange_partner_id'):
            super(AccountRegisterPayments, self)._onchange_partner_id()
        if self.partner_id and len(self.partner_id.bank_ids) > 0:
            self.partner_bank_account_id = self.partner_id.bank_ids[0]

    def get_payment_vals(self):
        res = super(AccountRegisterPayments, self).get_payment_vals()
        if self.payment_method_id == self.env.ref('account_sepa.account_payment_method_sepa_ct'):
            res.update({'partner_bank_account_id': self.partner_bank_account_id})
        return res

class AccountPayment(models.Model):
    _inherit = "account.payment"

    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")

    def _check_communication(self, payment_method_id, communication):
        super(AccountPayment, self)._check_communication(payment_method_id, communication)
        if payment_method_id == self.env.ref('account_sepa.account_payment_method_sepa_ct').id:
            if not communication:
                return
            if len(communication) > 140:
                raise ValidationError(_("A SEPA communication cannot exceed 140 characters"))
            check_valid_SEPA_str(communication)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if hasattr(super(AccountPayment, self), '_onchange_partner_id'):
            super(AccountPayment, self)._onchange_partner_id()
        if self.partner_id and len(self.partner_id.bank_ids) > 0:
            self.partner_bank_account_id = self.partner_id.bank_ids[0]
