# -*- coding: utf-8 -*-

import logging
import StringIO
from xml.etree import ElementTree

from openerp import api, models, _
from openerp.exceptions import UserError
try:
    from ofxparse import OfxParser
    from ofxparse.ofxparse import OfxParserException
except ImportError:
    logging.getLogger(__name__).warning("The ofxparse python library is not installed, ofx import will not work.")
    OfxParser = OfxParserException = None


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_ofx(self, data_file):
        try:
            root = ElementTree.fromstring(data_file)
            return root.tag.lower() == 'ofx'
        except ElementTree.ParseError:
            return False

    def _parse_file(self, data_file):
        if not self._check_ofx(data_file):
            return super(AccountBankStatementImport, self)._parse_file(data_file)
        if OfxParser is None:
            raise UserError(_("The library 'ofxparse' is missing, OFX import cannot proceed."))

        ofx = OfxParser.parse(StringIO.StringIO(data_file))
        transactions = []
        total_amt = 0.00
        for transaction in ofx.account.statement.transactions:
            # Since ofxparse doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
            # (normal behaviour is to provide 'account_number', which the generic module uses to find partner/bank)
            bank_account_id = partner_id = False
            partner_bank = self.env['res.partner.bank'].search([('partner_id.name', '=', transaction.payee)], limit=1)
            if partner_bank:
                bank_account_id = partner_bank.id
                partner_id = partner_bank.partner_id.id
            vals_line = {
                'date': transaction.date,
                'name': transaction.payee + (transaction.memo and ': ' + transaction.memo or ''),
                'ref': transaction.id,
                'amount': transaction.amount,
                'unique_import_id': transaction.id,
                'bank_account_id': bank_account_id,
                'partner_id': partner_id,
            }
            total_amt += float(transaction.amount)
            transactions.append(vals_line)

        vals_bank_statement = {
            'name': ofx.account.routing_number,
            'transactions': transactions,
            # WARNING: the provided ledger balance is not necessarily the ending balance of the statement
            # see https://github.com/odoo/odoo/issues/3003
            'balance_start': float(ofx.account.statement.balance) - total_amt,
            'balance_end_real': ofx.account.statement.balance,
        }
        return ofx.account.statement.currency, ofx.account.number, [vals_bank_statement]
