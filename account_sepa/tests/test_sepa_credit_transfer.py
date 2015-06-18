# -*- coding: utf-8 -*-

import base64
from lxml import etree

from openerp.addons.account.tests.account_test_classes import AccountingTestCase
from openerp.modules.module import get_module_resource

class TestSEPACreditTransfer(AccountingTestCase):

    def setUp(self):
        super(TestSEPACreditTransfer, self).setUp()

        # Get some records
        self.suppliers = self.env['res.partner'].search([('supplier', '=', True)])
        self.sepa_ct = self.env.ref('account_sepa.account_payment_method_sepa_ct')

        # Create an IBAN bank account and its journal
        self.bank_euro = self.env['res.partner.bank'].create({
            'state': 'iban',
            'company_id': self.env.ref('base.main_company').id,
            'partner_id': self.env.ref('base.main_company').partner_id.id,
            'acc_number': 'BE61310126985517',
            'bank_bic': 'BBRUBEBB',
            'bank_name': 'ING',
        })
        self.bank_journal = self.bank_euro.journal_id
        if self.bank_journal.company_id.currency_id != self.env.ref("base.EUR"):
            self.bank_journal.default_credit_account_id.write({'currency_id': self.env.ref("base.EUR").id})
            self.bank_journal.default_debit_account_id.write({'currency_id': self.env.ref("base.EUR").id})
            self.bank_journal.write({'currency_id': self.env.ref("base.EUR").id})

        # Make sure all suppliers have exactly one bank account
        self.setSingleBankAccountToPartner(self.suppliers[0], {
            'state': 'iban',
            'partner_id': self.suppliers[0].id,
            'acc_number': 'BE39103123456719',
            'bank_bic': 'NICABEBB',
            'bank_name': 'Crelan',
        })
        self.setSingleBankAccountToPartner(self.suppliers[1], {
            'state': 'iban',
            'partner_id': self.suppliers[1].id,
            'acc_number': 'SI56191000000123438',
            'bank_bic': 'CREGBEBB',
            'bank_name': 'CBC',
        })
        self.setSingleBankAccountToPartner(self.suppliers[2], {
            'state': 'bank',
            'partner_id': self.suppliers[2].id,
            'acc_number': '123456789',
            'bank_name': 'Mock & Co',
        })

        # Create 1 payment per supplier
        self.payment_1 = self.createPayment(self.suppliers[0], 500)
        self.payment_1.post()
        self.payment_2 = self.createPayment(self.suppliers[1], 600)
        self.payment_2.post()
        self.payment_3 = self.createPayment(self.suppliers[2], 700)
        self.payment_3.post()

        # Get a pain.001.001.03 schema validator
        schema_file_path = get_module_resource('account_sepa', 'schemas', 'pain.001.001.03.xsd')
        self.xmlschema = etree.XMLSchema(etree.parse(open(schema_file_path)))

    def setSingleBankAccountToPartner(self, partner_id, bank_account_vals):
        """ Make sure a partner has exactly one bank account """
        partner_id.bank_ids.unlink()
        return self.env['res.partner.bank'].create(bank_account_vals)

    def createPayment(self, partner, amount):
        """ Create a SEPA credit transfer payment """
        return self.env['account.payment'].create({
            'journal_id': self.bank_journal.id,
            'partner_bank_account_id': partner.bank_ids[0].id,
            'payment_method_id': self.sepa_ct.id,
            'payment_type': 'outbound',
            'payment_date': '2015-04-28',
            'amount': amount,
            'currency_id': self.env.ref("base.EUR").id,
            'partner_id': partner.id,
            'partner_type': 'supplier',
        })

    def testStandardSEPA(self):
        model_credit_transfer = self.env['account.sepa.credit.transfer']
        model_credit_transfer.create_sepa_credit_transfer(self.payment_1 | self.payment_2)
        credit_transfer = model_credit_transfer.search([], limit=1, order="id desc")
        self.assertFalse(credit_transfer.is_generic)
        sct_doc = etree.fromstring(base64.b64decode(credit_transfer.file))
        self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)
        self.assertEqual(self.payment_1.state, 'sent')
        self.assertEqual(self.payment_2.state, 'sent')

    def testGenericSEPA(self):
        model_credit_transfer = self.env['account.sepa.credit.transfer']
        model_credit_transfer.create_sepa_credit_transfer(self.payment_1 | self.payment_3)
        credit_transfer = model_credit_transfer.search([], limit=1, order="id desc")
        self.assertTrue(credit_transfer.is_generic)
        sct_doc = etree.fromstring(base64.b64decode(credit_transfer.file))
        self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)
        self.assertEqual(self.payment_1.state, 'sent')
        self.assertEqual(self.payment_3.state, 'sent')
