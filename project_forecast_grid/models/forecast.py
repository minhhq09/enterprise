# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from openerp import models, fields, api, _
import openerp.exceptions
from openerp.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    @api.multi
    def view_monthly_forecast(self):
        self.env.cr.execute("""
            SELECT count(*)
            FROM project_forecast
            WHERE project_id = %s
              AND date_trunc('month', start_date) != date_trunc('month', end_date);
        """, [self.id])
        [count] = self.env.cr.fetchone()
        if count:
            raise openerp.exceptions.UserError(
                _("Can only be used for forecasts not spanning multiple months, "
                  "found %(forecast_count)d forecast(s) spanning across "
                  "months in %(project_name)s") % {
                    'forecast_count': count,
                    'project_name': self.display_name,
                }
            )

        return {
            'name': _("Forecast"),
            'type': 'ir.actions.act_window',
            'res_model': 'project.forecast',
            'view_id': self.env.ref('project_forecast_grid.project_forecast_grid').id,
            'view_mode': 'grid',
            'domain': [['project_id', '=', self.id]],
            'context': {
                'default_project_id': self.id,
            }
        }

class Forecast(models.Model):
    _inherit = "project.forecast"

    def _grid_start_of(self, span, step, anchor):
        if span != 'project':
            return super(Forecast, self)._grid_start_of(span, step, anchor)

        project = self.env['project.project'].browse(self.env.context['default_project_id'])

        if step != 'month':
            raise openerp.exceptions.UserError(
                _("Forecasting over a project only supports monthly forecasts (got step {})").format(step)
            )
        if not project.date_start:
            raise openerp.exceptions.UserError(
                _("A project must have a start date to use a forecast grid, "
                  "found no start date for {project.display_name}").format(
                    project=project
                )
            )
        return fields.Date.from_string(project.date_start).replace(day=1)

    def _grid_end_of(self, span, step, anchor):
        if span != 'project':
            return super(Forecast, self)._grid_end_of(span, step, anchor)

        project = self.env['project.project'].browse(self.env.context['default_project_id'])
        if not project.date:
            raise openerp.exceptions.UserError(
                _("A project must have an end date to use a forecast grid, "
                  "found no end date for {project.display_name").format(
                    project=project
                )
            )
        return fields.Date.from_string(project.date)

    def _grid_pagination(self, field, span, step, anchor):
        if span != 'project':
            return super(Forecast, self)._grid_pagination(field, span, step, anchor)
        return False, False

    @api.multi
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'start_date' or cell_field != 'resource_hours':
            raise openerp.exceptions.UserError(
                _("Grid adjustment for project forecasts only supports the "
                  "'start_date' columns field and the 'resource_hours' cell "
                  "field, got respectively %(column_field)r and "
                  "%(cell_field)r") % {
                    'column_field': column_field,
                    'cell_field': cell_field,
                }
            )

        from_, to_ = map(fields.Date.from_string, column_value.split('/'))
        start = fields.Date.to_string(from_)
        # range is half-open get the actual end date
        end = fields.Date.to_string(to_ - relativedelta(days=1))

        # see if there is an exact match
        cell = self.search(expression.AND([row_domain, [
            '&',
            ['start_date', '=', start],
            ['end_date', '=', end]
        ]]), limit=1)
        # if so, adjust in-place
        if cell:
            cell[cell_field] += change
            return False

        # otherwise copy an existing cell from the row, ignore eventual
        # non-monthly forecast
        # TODO: maybe expand the non-monthly forecast to a fully monthly forecast?
        self.search(row_domain, limit=1).ensure_one().copy({
            'start_date': start,
            'end_date': end,
            cell_field: change,
        })
        return False

    @api.model
    def _read_forecast_tasks(self, task_ids, domain, read_group_order=None, access_rights_uid=None):
        Tasks = self.env['project.task']
        if access_rights_uid:
            Tasks = Tasks.sudo(access_rights_uid)

        tasks_domain = [('id', 'in', task_ids)]
        if 'default_project_id' in self.env.context:
            tasks_domain = expression.OR([
                tasks_domain,
                [('project_id', '=', self.env.context['default_project_id'])]
            ])
        ids = Tasks._search(tasks_domain)
        return Tasks.browse(ids).name_get(), dict.fromkeys(ids, False)


    _group_by_full = {
        'task_id': _read_forecast_tasks
    }
