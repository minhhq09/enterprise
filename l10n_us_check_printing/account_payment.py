# -*- coding: utf-8 -*-

from openerp import models, api, _

class account_payment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def print_checks(self):
        us_check_layout = self[0].company_id.us_check_layout
        if us_check_layout != 'disabled':
            # TODO: this should be moved to account_check_writing / account_payment.py / send_checks
            # when account_check_writing becomes account_check_printing_commons
            if not self[0].journal_id.check_manual_sequencing:
                # The wizard asks for the number printed on the first pre-printed check
                # so payments are attributed the number of the check the'll be printed on.
                last_printed_check = self.search([
                    ('journal_id', '=', self[0].journal_id.id),
                    ('check_number', '!=', 0)], order="check_number desc", limit=1)
                next_check_number = last_printed_check and last_printed_check.check_number + 1 or 1
                return {
                    'name': _('Print Pre-numbered Checks'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'print.prenumbered.checks',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'payment_ids': self.ids,
                        'default_next_check_number': next_check_number,
                    }
                }
            else:
                return self.do_print_checks()
        super(account_payment, self).print_checks()

    @api.multi
    def do_print_checks(self):
        return self.env['report'].get_action(self, self[0].company_id.us_check_layout)
