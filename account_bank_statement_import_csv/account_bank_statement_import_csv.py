# -*- coding: utf-8 -*-

import base64

import dateutil.parser
import StringIO

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _check_csv(self, filename):
        return filename and filename.strip().endswith('.csv')

    @api.multi
    def import_file(self):
        if not self._check_csv(self.filename):
            return super(AccountBankStatementImport, self).import_file()
        ctx = dict(self.env.context)
        import_wizard = self.env['base_import.import'].create({'res_model': 'account.bank.statement.line',
                                                'file': base64.b64decode(self.data_file),
                                                'file_name': self.filename,
                                                'file_type': 'text/csv'})
        ctx['wizard_id'] = import_wizard.id
        return {
                'type': 'ir.actions.client',
                'tag': 'import_bank_stmt',
                'params': {
                    'model': 'account.bank.statement.line',
                    'context': ctx,
                    'filename': self.filename,
                    }
                }


class AccountBankStmtImportCSV(models.TransientModel):
    _inherit = 'base_import.import'

    def get_fields(self, cr, uid, model, context=None,
                   depth=2):
        fields = super(AccountBankStmtImportCSV, self).get_fields(cr, uid, model, context=context, depth=depth)
        if context.get('bank_stmt_import', False):
            add_fields = [{
                'id': 'balance',
                'name': 'balance',
                'string': 'Balance',
                'required': False,
                'fields': [],
                'type': 'monetary',
            },{
                'id': 'debit',
                'name': 'debit',
                'string': 'Debit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            },{
                'id': 'credit',
                'name': 'credit',
                'string': 'Credit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }]
            fields.extend(add_fields)
        return fields

    def _parse_import_data(self, cr, uid, data, import_fields, record, options, context=None):
        data = super(AccountBankStmtImportCSV, self)._parse_import_data(cr, uid, data, import_fields, record, options, context)
        statement_id = context.get('bank_statement_id', False)
        if statement_id:
            import_fields.append('statement_id/.id')
            convert_to_amount = False
            if 'debit' in import_fields and 'credit' in import_fields:
                index_debit = import_fields.index('debit')
                index_credit = import_fields.index('credit')
                self._parse_float_from_data(cr, uid, data, index_debit, 'debit', options, context=context)
                self._parse_float_from_data(cr, uid, data, index_credit, 'credit', options, context=context)
                import_fields.remove('debit')
                import_fields.remove('credit')
                import_fields.append('amount')
                convert_to_amount = True
            # add starting balance and ending balance to context
            if 'balance' in import_fields:
                index_balance = import_fields.index('balance')
                self._parse_float_from_data(cr, uid, data, index_balance, 'balance', options, context=context)
                context['starting_balance'] = float(data[0][index_balance])
                context['starting_balance'] -= float(data[0][import_fields.index('amount')]) if not convert_to_amount else float(data[0][index_debit])-float(data[0][index_credit])
                context['ending_balance'] = data[len(data)-1][index_balance]
                import_fields.remove('balance')
            for line in data:
                line.append(statement_id)
                if convert_to_amount:
                    line.append(float(line[index_debit])-float(line[index_credit]))
                    line.remove(line[index_debit])
                    line.remove(line[index_credit])
                if index_balance:
                    line.remove(line[index_balance])
            if 'date' in import_fields:
                context['date'] = data[len(data)-1][import_fields.index('date')]

        return data

    def parse_preview(self, cr, uid, id, options, count=10, context=None):
        if context is None:
            context = {}
        updated_context = context.copy()
        if options.get('bank_stmt_import', False):
            updated_context.update({'bank_stmt_import': True})
        return super(AccountBankStmtImportCSV, self).parse_preview(cr, uid, id, options, count=count, context=updated_context)
                

    def do(self, cr, uid, id, fields, options, dryrun=False, context=None):
        if options.get('bank_stmt_import', False):
            cr.execute('SAVEPOINT import_bank_stmt')
            vals = {'journal_id': context.get('journal_id', False), 'reference': self.browse(cr, uid, id)['file_name']}
            statement_id = self.pool.get('account.bank.statement').create(cr, uid, vals, context=context)
            ctx = context.copy()
            ctx['bank_statement_id'] = statement_id
            res = super(AccountBankStmtImportCSV, self).do(cr, uid, id, fields, options, dryrun=dryrun, context=ctx)
            # add starting balance and date if there is one set in fields
            if ctx.get('starting_balance', False):
                vals = {'balance_start': ctx.get('starting_balance'), 'balance_end_real': ctx.get('ending_balance')}
            if ctx.get('date', False):
                vals.update({'date': ctx.get('date')})
            if ctx.get('starting_balance', False) or ctx.get('date', False):
                self.pool.get('account.bank.statement').write(cr, uid, statement_id, vals, context=ctx)
            try:
                if dryrun:
                    cr.execute('ROLLBACK TO SAVEPOINT import_bank_stmt')
                else:
                    cr.execute('RELEASE SAVEPOINT import_bank_stmt')
            except psycopg2.InternalError:
                pass
            return res
        else:
            return super(AccountBankStmtImportCSV, self).do(cr, uid, id, fields, options, dryrun=dryrun, context=context)