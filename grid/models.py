# -*- coding: utf-8 -*-

import collections
from functools import partial

import babel.dates
from dateutil.relativedelta import relativedelta, MO, SU

from openerp import _, api, fields, models
from openerp.osv import expression

_GRID_TUP = [('grid', "Grid")]


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=_GRID_TUP)

class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=_GRID_TUP)

class Model(models.Model):
    _inherit = 'base'

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None):
        """
        Current anchor (if sensible for the col_field) can be provided by the
        ``grid_anchor`` value in the context

        :param list[str] row_fields: group row header fields
        :param str col_field: column field
        :param str cell_field: cell field, summed
        :param range: displayed range for the current page
        :type range: None | {'step': object, 'span': object}
        :type domain: None | list
        :returns: dict of prev context, next context, matrix data, row values
                  and column values
        """
        column_info = self._grid_column_info(col_field, range)

        # [{ __count, __domain, grouping, **row_fields, cell_field }]
        groups = self._read_group_raw(
            expression.AND([expression.normalize_domain(domain), column_info.domain]),
            [col_field, cell_field] + row_fields,
            [column_info.grouping] + row_fields,
            lazy=False
        )

        row_key = lambda it, fs=row_fields: tuple(it[f] for f in fs)

        # [{ values: { field1: value1, field2: value2 } }]
        rows = self._grid_get_row_headers(row_fields, groups, key=row_key)
        # column_info.values is a [(value, label)] seq
        # convert to [{ values: { col_field: (value, label) } }]
        cols = column_info.values

        # map of cells indexed by row_key (tuple of row values) then column value
        cell_map = collections.defaultdict(dict)
        for group in groups:
            row = row_key(group)
            col = column_info.format(group[column_info.grouping])
            cell_map[row][col] = self._grid_format_cell(group, cell_field)

        # pre-build whole grid, row-major, h = len(rows), w = len(cols),
        # each cell is
        #
        # * size (number of records)
        # * value (accumulated cell_field)
        # * domain (domain for the records of that cell
        grid = []
        for r in rows:
            row = []
            grid.append(row)
            r_k = row_key(r['values'])
            for c in cols:
                col_value = c['values'][col_field][0]
                it = cell_map[r_k].get(col_value)
                if it: # accumulated cell exists, just use it
                    row.append(it)
                else:
                    # generate de novo domain for the cell
                    d = expression.normalize_domain([
                        # TODO: how to convert value out of read to domain section?
                        (f, '=', v if isinstance(v, (basestring, bool, int, long, float)) else v[0])
                        for f, v in r['values'].iteritems()
                    ])
                    d = expression.AND([d, c['domain']])
                    row.append(self._grid_make_empty_cell(d))
                row[-1]['is_current'] = c.get('is_current', False)

        return {
            'prev': column_info.prev,
            'next': column_info.next,
            'cols': cols,
            'rows': rows,
            'grid': grid,
        }

    def _grid_make_empty_cell(self, cell_domain):
        return {'size': 0, 'domain': cell_domain, 'value': 0}

    def _grid_format_cell(self, group, cell_field):
        return {
            'size': group['__count'],
            'domain': group['__domain'],
            'value': group[cell_field],
        }

    def _grid_get_row_headers(self, row_fields, groups, key):
        seen = {}
        rows = []
        for cell in groups:
            k = key(cell)
            if k in seen:
                seen[k][1].append(cell['__domain'])
            else:
                r = (
                    {f: cell[f] for f in row_fields},
                    [cell['__domain']],
                )
                seen[k] = r
                rows.append(r)

        # TODO: generates pretty long domains, is there a way to simplify them?
        return [
            {'values': values, 'domain': expression.OR(domains)}
            for values, domains in rows
        ]

    def _grid_column_info(self, name, range):
        """
        :param str name:
        :param range:
        :type range: None | dict
        :rtype: ColumnMetadata
        """
        if not range:
            range = {}
        field = self._fields[name]
        context_anchor = self.env.context.get('grid_anchor')

        if field.type == 'selection':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                values=[{
                        'values': { name: v },
                        'domain': [(name, '=', v[0])],
                        'is_current': False
                    } for v in field._description_selection(self.env)
                ],
                format=lambda a: a,
            )
        elif field.type == 'many2one':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                values=[{
                        'values': { name: v },
                        'domain': [(name, '=', v[0])],
                        'is_current': False
                    } for v in self.env[field.comodel_name].search([]).name_get()
                ],
                format=lambda a: a and a[0],
            )
        elif field.type == 'date':
            # seemingly sane defaults
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            today = anchor = field.from_string(field.context_today(self))
            if context_anchor:
                anchor = field.from_string(context_anchor)

            labelize = partial(babel.dates.format_date,
                               format=FORMAT[step],
                               locale=self.env.context.get('lang', 'en_US'))
            r = self._grid_range_of(span, anchor)

            period_prev, period_next = self._grid_pagination(field, span, anchor)
            return ColumnMetadata(
                grouping='{}:{}'.format(name, step),
                domain=[
                    '&',
                    (name, '>=', field.to_string(r.start)),
                    (name, '<=', field.to_string(r.end))
                ],
                prev=period_prev and {'grid_anchor': period_prev, 'default_%s' % name: period_prev},
                next=period_next and {'grid_anchor': period_next, 'default_%s' % name: period_next},
                values=[{
                        'values': {
                            name: (
                                "%s/%s" % (field.to_string(d), field.to_string(d + self._grid_step_by(step))),
                                labelize(d)
                        )},
                        'domain': ['&',
                                   (name, '>=', field.to_string(d)),
                                   (name, '<', field.to_string(d + self._grid_step_by(step)))],
                        'is_current': d == today,
                    } for d in r.iter(step)
                ],
                format=lambda a: a and a[0],
            )
        else:
            raise ValueError(_("Can not use fields of type %s as grid columns") % field.type)

    def _grid_pagination(self, field, span, anchor):
        if field.type == 'date':
            diff = self._grid_step_by(span)
            period_prev = field.to_string(anchor - diff)
            period_next = field.to_string(anchor + diff)
            return period_prev, period_next
        return False, False

    def _grid_step_by(self, span):
        return STEP_BY.get(span)

    def _grid_range_of(self, span, anchor):
        return date_range(self._grid_start_of(span, anchor),
                          self._grid_end_of(span, anchor))

    def _grid_start_of(self, span, anchor):
        return anchor + START_OF[span]

    def _grid_end_of(self, span, anchor):
        return anchor + END_OF[span]


ColumnMetadata = collections.namedtuple('ColumnMetadata', 'grouping domain prev next values format')
class date_range(object):
    def __init__(self, start, stop):
        assert start < stop
        self.start = start
        self.end = stop

    def iter(self, step):
        v = self.start
        step = STEP_BY[step]
        while v <= self.end:
            yield v
            v += step

START_OF = {
    'week': relativedelta(weekday=MO(-1)),
    'month': relativedelta(day=1),
    'year': relativedelta(yearday=1),
}
END_OF = {
    'week': relativedelta(weekday=SU),
    'month': relativedelta(months=1, day=1, days=-1),
    'year': relativedelta(years=1, yearday=1, days=-1),
}
STEP_BY = {
    'day': relativedelta(days=1),
    'week': relativedelta(weeks=1),
    'month': relativedelta(months=1),
    'year': relativedelta(years=1),
}
FORMAT = {
    'day': u"EEE\nMMM\u00A0dd",
    'month': u'MMMM\u00A0yyyy',
}
