# Make sure / performs a floating point division even if environment is python 2
from __future__ import division

from openerp.addons.account_check_printing.tests.test_check_printing import TestCheckPrinting
from openerp.addons.l10n_us_check_printing.report import print_check

import math

class TestPrintCheck(TestCheckPrinting):

    def setUp(self):
        super(TestPrintCheck, self).setUp()
        self.check_report = print_check.report_print_check(self.env.cr, self.env.uid, 'test', self.env.context)

    def test_print_check(self):
        # Make a payment for 10 invoices and 5 refunds
        invoices = self.env['account.invoice']
        for i in range(0,15):
            invoices |= self.create_invoice(is_refund=(i%3 == 0))
        payment = self.create_payment(invoices)

        # Check the data generated for the report
        self.env.ref('base.main_company').write({'us_check_multi_stub': True})
        report_pages = self.check_report.get_pages(payment)
        self.assertEqual(len(report_pages), int(math.ceil(len(invoices.ids) / print_check.INV_LINES_PER_STUB)))
        self.env.ref('base.main_company').write({'us_check_multi_stub': False})
        report_pages = self.check_report.get_pages(payment)
        self.assertEqual(len(report_pages), 1)
