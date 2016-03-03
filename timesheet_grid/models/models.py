# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from odoo.addons.grid.models import END_OF


class AnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        copy_data = super(AnalyticLine, self)\
            .copy_data(cr, uid, id, default=default, context=context)
        if not default or 'name' not in default:
            # don't keep the current description for the new copied line
            copy_data['name'] = u'/'
        if not default or 'amount' not in default:
            # also reset the amount
            copy_data['amount'] = 0
        return copy_data

    @api.multi
    def validate(self):
        employees = self.mapped('user_id.employee_ids')
        anchor = fields.Date.from_string(self.env.context['grid_anchor'])
        span = self.env.context['grid_range']['span']
        validate_to = anchor + END_OF[span]
        employees.write({'timesheet_validated': fields.Date.to_string(validate_to)})
        return ()

    @api.model
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'date' or cell_field != 'unit_amount':
            raise ValueError(
                "{} can only adjust unit_amount (got {}) by date (got {})".format(
                self._name,
                cell_field,
                column_field,
            ))

        # span is always daily and value is an iso range
        day = column_value.split('/')[0]

        self.search(row_domain, limit=1).copy({
            column_field: day,
            cell_field: change
        })
        return False

class Employee(models.Model):
    _inherit = 'hr.employee'

    timesheet_validated = fields.Date(
        "Timesheets validation limit",
        help="Date until which the employee's timesheets have been validated")
