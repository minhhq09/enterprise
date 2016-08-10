# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_statements_source = fields.Selection(selection_add=[("online_sync", "Bank Synchronization")])
