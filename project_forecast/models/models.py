# -*- coding: utf-8 -*-
from datetime import date, datetime, time, timedelta

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from openerp.osv import expression

class User(models.Model):
    _inherit = 'res.users'

    resource_ids = fields.One2many('resource.resource', 'user_id')

class ProjectForecast(models.Model):
    _name = 'project.forecast'

    def default_user_id(self):
        return self.env.context.get('default_user_id', self.env.uid)

    def default_end_date(self):
        return date.today() + timedelta(days=1)

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string="User", required=True,
                              default=default_user_id)
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2one('project.task', string="Task", domain="[('project_id', '=', project_id)]")

    # used in custom filter
    stage_id = fields.Many2one(related='task_id.stage_id', string="Task stage")
    tag_ids = fields.Many2many(related='task_id.tag_ids', string="Task tags")

    time = fields.Float(string="%", help="Percentage of working time", compute='_compute_time', store=True)

    start_date = fields.Date(default=fields.Date.today, required="True")
    end_date = fields.Date(default=default_end_date, required="True")

    # consolidation color and exclude
    color = fields.Integer(string="Color", compute='_compute_color')
    exclude = fields.Boolean(string="Exclude", compute='_compute_exclude', store=True)

    # resource
    resource_hours = fields.Float(string="Planned hours", default=0)
    effective_hours = fields.Float(string="Effective hours", compute='_compute_effective_hours', store=True)
    percentage_hours = fields.Float(string="Progress", compute='_compute_percentage_hours', store=True)

    @api.one
    @api.depends('project_id', 'task_id', 'user_id')
    def _compute_name(self):
        group = self.env.context.get("group_by", "")

        name = []
        if ("user_id" not in group):
            name.append(self.user_id.name)
        if ("project_id" not in group and self.project_id):
            name.append(self.project_id.name)
        if ("task_id" not in group and self.task_id):
            name.append(self.task_id.name)

        if name:
            self.name = " - ".join(name)
        else:
            self.name = _("undefined")

    @api.one
    @api.depends('project_id.color')
    def _compute_color(self):
        self.color = self.project_id.color or 0

    @api.one
    @api.depends('project_id.name')
    def _compute_exclude(self):
        self.exclude = (self.project_id.name == "Leaves")

    @api.one
    @api.depends('resource_hours', 'start_date', 'end_date', 'user_id.resource_ids.calendar_id')
    def _compute_time(self):
        start = fields.Datetime.from_string(self.start_date)
        stop = fields.Datetime.from_string(self.end_date)
        calendar = self.mapped('user_id.resource_ids.calendar_id')
        if calendar:
            hours = calendar[0].get_working_hours(start, stop)
            self.time = self.resource_hours * 100.0 / hours
        else:
            self.time = 0

    @api.one
    @api.depends('task_id', 'user_id', 'start_date', 'end_date', 'project_id.analytic_account_id')
    def _compute_effective_hours(self):
        if not self.task_id and not self.project_id:
            self.effective_hours = 0
        else:
            aac_obj = self.env['account.analytic.line']
            aac_domain = [
                ('user_id', '=', self.user_id.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ]
            # TODO: move this to a link module. This checks that the project_timesheet module is installed.
            if self.task_id and hasattr(self.task_id, 'analytic_account_id'):
                timesheets = aac_obj.search(expression.AND([[('task_id', '=', self.task_id.id)], aac_domain]))
            elif self.project_id:
                timesheets = aac_obj.search(expression.AND([[('account_id', '=', self.project_id.analytic_account_id.id)], aac_domain]))
            else:
                timesheets = aac_obj.browse()

            self.effective_hours = sum(timesheet.unit_amount for timesheet in timesheets)

    @api.one
    @api.depends('resource_hours', 'effective_hours')
    def _compute_percentage_hours(self):
        if self.resource_hours:
            self.percentage_hours = self.effective_hours / self.resource_hours
        else:
            self.percentage_hours = 0

    @api.one
    @api.constrains('resource_hours')
    def _check_time_positive(self):
        if self.resource_hours and (self.resource_hours < 0):
            raise ValidationError(_("Forecasted time must be positive"))

    @api.one
    @api.constrains('task_id', 'project_id')
    def _task_id_in_project(self):
        if self.project_id and self.task_id and (self.task_id not in self.project_id.tasks):
            raise ValidationError(_("Your task is not in the selected project."))

    @api.one
    @api.constrains('start_date', 'end_date')
    def _start_date_lower_end_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("The start-date must be lower than end-date."))

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.task_id:
            self.project_id = self.task_id.project_id

    @api.onchange('project_id')
    def _onchange_project_id(self):
        domain = [] if not self.project_id else [('project_id', '=', self.project_id.id)]
        return {
            'domain': {'task_id': domain},
        }

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.end_date < self.start_date:
            start = fields.Date.from_string(self.start_date)
            duration = timedelta(days=1)
            self.end_date = start + duration

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.start_date > self.end_date:
            end = fields.Date.from_string(self.end_date)
            duration = timedelta(days=1)
            self.start_date = end - duration

    @api.multi
    def all_users(self, domain, read_group_order=None, access_rights_uid=None):
        group = self.env.ref('project.group_project_user') or self.env.ref('base.group_user')
        name = group.users.name_get()
        return name, None

    _group_by_full = {
        'user_id': all_users,
    }


class Project(models.Model):
    _inherit = 'project.project'

    allow_forecast = fields.Boolean("Allow forecast", default=False, help="This feature shows the Forecast link in the kanban view")

    @api.multi
    def write(self, vals):
        if 'active' in vals:
            self.env['project.forecast'].with_context(active_test=False).search([('project_id', 'in', self.ids)]).write({'active': vals['active']})
        return super(Project, self).write(vals)

    @api.multi
    def create_forecast(self):
        view_id = self.env.ref('project_forecast.project_forecast_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.forecast',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {
                'default_project_id': self.id,
                'default_user_id': self.user_id.id,
            }
        }


class Task(models.Model):
    _inherit = 'project.task'

    @api.multi
    def create_forecast(self):
        view_id = self.env.ref('project_forecast.project_forecast_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.forecast',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
                'default_user_id': self.user_id.id,
            }
        }
