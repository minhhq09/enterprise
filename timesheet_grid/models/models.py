# -*- coding: utf-8 -*-
import itertools

from openerp import models, fields, api, _
from odoo.addons.grid.models import END_OF


class AnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # don't keep existing description (if any) when copying a line
    name = fields.Char(required=False, copy=False)
    # reset amount on copy
    amount = fields.Monetary(copy=False)
    validated = fields.Boolean("Validated line", compute='_timesheet_line_validated', store=True)
    project_id = fields.Many2one(domain=[('allow_timesheets', '=', True)])
    is_timesheet = fields.Boolean(
        string="Timesheet Line",
        compute='_compute_is_timesheet', search='_search_is_timesheet',
        help="Set if this analytic line represents a line of timesheet.")

    @api.multi
    @api.depends('project_id')
    def _compute_is_timesheet(self):
        for line in self:
            line.is_timesheet = bool(line.project_id)

    def _search_is_timesheet(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('project_id', '!=', False)]

        return [('project_id', '=', False)]

    @api.multi
    def validate(self):
        anchor = fields.Date.from_string(self.env.context['grid_anchor'])
        span = self.env.context['grid_range']['span']
        validate_to = fields.Date.to_string(anchor + END_OF[span])

        validation = self.env['timesheet_grid.validation'].create({
            'validate_to': validate_to,
            'validable_ids': [
                (0, None, {'employee_id': employee.id})
                for employee in self.mapped('user_id.employee_ids')
                if not employee.timesheet_validated \
                    or employee.timesheet_validated < validate_to
            ]
        })

        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'timesheet_grid.validation',
            'res_id': validation.id,
            'views': [(False, 'form')],
        }

    @api.multi
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
    @api.multi
    @api.depends('date', 'user_id.employee_ids.timesheet_validated')
    def _timesheet_line_validated(self):
        for line in self:
            # get most recent validation date on any of the line user's
            # employees
            validated_to = max(itertools.chain((
                e.timesheet_validated
                for e in line.user_id.employee_ids
            ), [None]))
            if validated_to:
                line.validated = line.date <= validated_to
            else:
                line.validated = False

class Employee(models.Model):
    _inherit = 'hr.employee'

    timesheet_validated = fields.Date(
        "Timesheets validation limit",
        help="Date until which the employee's timesheets have been validated")

class Project(models.Model):
    _inherit = 'project.project'

    allow_timesheets = fields.Boolean("Allow timesheets", default=True)

class Validation(models.TransientModel):
    _name = 'timesheet_grid.validation'

    validate_to = fields.Date()
    validable_ids = fields.One2many('timesheet_grid.validable', 'validation_id')

    # Recompute SO Lines delivered at validation
    @api.multi
    def validate(self):
        employees = self.validable_ids.filtered('validate').mapped('employee_id')
        mdate = min(employees.mapped('timesheet_validated'))
        employees.write({'timesheet_validated': self.validate_to})
        # could be improved by filtering on date delta only
        self.env['account.analytic.line'].search(['&', ('date','>',mdate), ('is_timesheet', '=', True), ('user_id', 'in', employees.mapped('user_id').ids)]) \
            .mapped('so_line') \
            .sudo() \
            ._compute_analytic()
        return ()

class Validable(models.TransientModel):
    _name = 'timesheet_grid.validable'

    validation_id = fields.Many2one('timesheet_grid.validation', required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    validate = fields.Boolean(
        default=True, help="Validate this employee's timesheet up to the chosen date")
