odoo.define('web_grid', function (require) {
"use strict";

var Class = require('web.Class');
var View = require('web.View');
var Widget = require('web.Widget');

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var formats = require('web.formats');
var time = require('web.time');
var utils = require('web.utils');
var session = require('web.session');
var pyeval = require('web.pyeval');

var patch = require('snabbdom.patch');
var h = require('snabbdom.h');

var _t = core._t;
var _lt = core._lt;

var Field = Class.extend({
    init: function (name, descr, arch) {
        this._field_name = name;
        this._descr = descr;
        this._arch = arch || {attrs: {}, children: []};
    },
    self: function (record) {
        return record[this._field_name];
    },

    name: function () {
        return this._field_name;
    },

    label: function (record) {
        return this.self(record);
    },
    value: function (record) {
        return this.self(record);
    },

    format: function (value) {
        var type = this._arch.attrs.widget || this._descr.type;

        return formats.format_value(value, { type: type });
    },
    parse: function (value) {
        var type = this._arch.attrs.widget || this._descr.type;

        return formats.parse_value(value, { type: type });
    },
});
var fields = { };

var GridView = View.extend({
    icon: 'fa-th-list',
    view_type: 'grid',
    add_label: _lt("Add a Line"),
    events: {
        "click .o_grid_button_add": function(event) {
            var _this = this;
            event.preventDefault();

            var ctx = pyeval.eval('context', _this._model.context());
            var form_context = _this.get_full_context();
            var formDescription = _this.ViewManager.views.form;
            var p = new form_common.FormViewDialog(this, {
                res_model: _this._model.name,
                res_id: false,
                // TODO: document quick_create_view (?) context key
                view_id: ctx['quick_create_view'] || (formDescription && formDescription.view_id) || false,
                context: form_context,
                title: _this.add_label,
                disable_multiple_selection: true,
            }).open();
            p.on('create_completed', this, function () {
                _this._fetch();
            });
        },
        'keydown .o_grid_input': function (e) {
            // suppress [return]
            switch (e.which) {
            case $.ui.keyCode.ENTER:
                e.preventDefault();
                e.stopPropagation();
                break;
            }
        },
        'blur .o_grid_input': function (e) {
            var $target = $(e.target);

            var row_index = $target.parent().data('row');
            var col_index = $target.parent().data('column');
            var data = this.get('grid_data');
            var cell = data.grid[row_index][col_index];

            try {
                var val = this._cell_field.parse(e.target.textContent.trim());
                $target.removeClass('has-error');
            } catch (_) {
                $target.addClass('has-error');
                return;
            }

            this.adjust({
                row: data.rows[row_index],
                col: data.cols[col_index],
                //ids: cell.ids,
                value: cell.value
            }, val)
        },
        'focus .o_grid_input': function (e) {
            var selection = window.getSelection();
            var range = document.createRange();
            range.selectNodeContents(e.target);
            selection.removeAllRanges();
            selection.addRange(range);
        },
        'click .o_grid_cell_information': function (e) {
            var $target = $(e.target);
            var grid = this.get('grid_data').grid;
            var cell = grid[$target.parent().data('row')]
                           [$target.parent().data('column')];

            var anchor, col = this._col_field.name();
            var additional_context = {};
            if (anchor = this.get('anchor')) {
                additional_context['default_' + col] = anchor;
            }

            var views = this.ViewManager.views;
            this.do_action({
                type: 'ir.actions.act_window',
                name: _t("Grid Cell Details"),
                res_model: this._model.name,
                views: [
                    [views.list ? views.list.view_id : false, 'list'],
                    [views.form ? views.form.view_id : false, 'form']
                ],
                domain: cell.domain,
                context: this._model.context(additional_context),
            });
        }
    },
    init: function (parent, dataset) {
        this._super.apply(this, arguments);

        this._model = dataset._model;

        this._col_field = null;
        this._cell_field = null;

        this._in_waiting = null;
        this._fetch_mutex = new utils.Mutex();

        this.on('change:grid_data', this, this._render);
        this.on('change:range', this, this._fetch);
        this.on('change:pagination_context', this, this._fetch);
    },
    start: function () {
        this._col_field = this._fields_of_type('col')[0];
        this._cell_field = this._fields_of_type('measure')[0];

        // this is the vroot, the first patch call will replace the DOM node
        // itself instead of patching it in-place, so we're losing delegated
        // events if the state is the root node
        this._state = document.createElement('div');
        this.el.appendChild(this._state);

        this._render();
        return $.when();
    },
    _render: function () {
        var _this = this;
        var grid_data = this.get('grid_data') || {};
        var columns = grid_data.cols || [];
        var rows = grid_data.rows || [];
        var grid = grid_data.grid || [];
        var col_field = this._col_field.name();
        var group_fields = this.get('groupby');

        var super_total = 0;
        var row_totals = {};
        var column_totals = {};
        for (var i = 0; i < grid.length; i++) {
            var row = grid[i];
            for (var j = 0; j < row.length; j++) {
                var cell = row[j];

                super_total += cell.value;
                row_totals[i] = (row_totals[i] || 0) + cell.value;
                column_totals[j] = (column_totals[j] || 0) + cell.value;
            }
        }

        var vnode = h('div.o_view_grid', [
            h('table.table.table-condensed.table-responsive.table-striped', [
                h('thead', [
                    h('tr', [
                        h('th.o_grid_title_header'),
                        h('th.o_grid_title_header'),
                    ].concat(
                        columns.map(function (column) {
                            return h('th', {class: {o_grid_current: column.is_current}},
                                column.values[col_field][1]
                            );
                        }),
                        [h('th.o_grid_total', _t("Total"))]
                    ))
                ]),
                h('tfoot', [
                    h('tr', [
                        h('td.o_grid_add_line', _this.is_action_enabled('create') && [
                            h('button.btn.btn-sm.btn-primary.o_grid_button_add', {
                                attrs: {type: 'button'}
                            }, _this.add_label.toString())
                        ]),
                        h('td.o_grid_total', _t("Total"))
                    ].concat(
                        columns.map(function (column, column_index) {
                            return h('td', {class: {
                                o_grid_total: true,
                                o_grid_current: column.is_current,
                            }}, _this._cell_field.format(
                                column_totals[column_index]
                            ))
                        }),
                        [h('td.o_grid_total', _this._cell_field.format(
                            super_total
                        ))]
                    ))
                ]),
                h('tbody', grid.map(function (row, row_index) {
                    var row_values = [];
                    for (var i = 0; i < group_fields.length; i++) {
                        var row_field = group_fields[i];
                        var value = rows[row_index].values[row_field];
                        if (value) {
                            row_values.push(value);
                        }
                    }
                    var row_key = row_values.map(function (v) {
                        return v[0]
                    }).join('|');
                    return h('tr', {key: row_key}, [
                        h('th', {attrs: {colspan: 2}}, [
                            h('div', row_values.map(function (v) {
                                return h('div', {attrs: {title: v[1]}}, v[1]);
                            }))
                        ]),
                    ].concat(
                        row.map(function (cell, cell_index) {
                            var cell_value = _this._cell_field.format(cell.value);
                            return h('td', {class: {o_grid_current: cell.is_current}}, [
                                h('div', {
                                    class: {
                                        o_grid_cell_container: true,
                                        o_grid_cell_empty: !cell.size
                                    },
                                    attrs: {
                                        'data-row': row_index,
                                        'data-column': cell_index,
                                    }
                                }, [
                                    h('i.fa.fa-info-circle.o_grid_cell_information', []),
                                    _this.is_action_enabled('edit')
                                        ? h('div.o_grid_input', {attrs: {
                                              contentEditable: "true"}
                                          }, cell_value)
                                        : h('div.o_grid_show', cell_value)
                                ])
                            ]);
                        }),
                        [h('td.o_grid_total', _this._cell_field.format(
                            row_totals[row_index]
                        ))]
                    ));
                }).concat(_(Math.max(5 - rows.length, 0)).times(function () {
                    return h('tr.o_grid_padding', [
                        h('th', {attrs: {colspan: '2'}}, '\u00A0')
                    ].concat(
                        columns.map(function (column) {
                            return h('td', {class: {o_grid_current: column.is_current}}, []);
                        }),
                        [h('td.o_grid_total', [])]
                    ));
                })))
            ])
        ]);
        if (!grid.length) {
            vnode.children.push(h('div.o_grid_nocontent_container', [
                h('div.oe_view_nocontent oe_edit_only', [
                    h('p.oe_view_nocontent_create', _t("Click to add projects and tasks")),
                    h('p', _t("You will be able to register your working hours on the given task"))
                ])
            ]));
        }

        this._state = patch(this._state, vnode);

        // need to debounce so grid can render
        setTimeout(function () {
            var row_headers = _this.el.querySelectorAll('tbody th:first-child div');
            for (var k = 0; k < row_headers.length; k++) {
                var header = row_headers[k];
                if (header.scrollWidth > header.clientWidth) {
                    $(header).addClass('overflow');
                }
            }
        }, 0);
    },
    do_show: function() {
        this.do_push_state({});
        return this._super();
    },
    get_ids: function () {
        var data = this.get('grid_data');
        var grid = data.grid;
        // if there are no elements in the grid we'll get an empty domain
        // which will select all records of the model... that is *not* what
        // we want
        if (!grid.length) {
            // ensure whatever's waiting on the ids never gets them
            return $.Deferred().reject().promise();
        }

        var domain = [];
        // count number of non-empty cells and only add those to the search
        // domain, on sparse grids this makes domains way smaller
        var cells = 0;
        for (var i = 0; i < grid.length; i++) {
            var row = grid[i];
            for (var j = 0; j < row.length; j++) {
                var cell = row[j];
                if (cell.size != 0) {
                    cells++;
                    domain.push.apply(domain, cell.domain);
                }
            }
        }
        while (--cells > 0) {
            domain.unshift('|');
        }

        return this._model.call('search', [domain], {context: this.get_full_context()})
    },
    get_full_context: function (ctx) {
        var c = this._model.context(this.get('context'));
        if (this.get('pagination_context')) {
            c.add(this.get('pagination_context'));
        }
        // probably not ideal, needs to be kept in sync with arrows
        if (this.get('range')) {
            c.add({'grid_range': this.get('range')});
        }
        if (ctx) {
            c.add(ctx);
        }
        return c;
    },

    do_search: function (domain, context, groupby) {
        this.set({
            'domain': domain,
            'context': context,
            'groupby': (groupby && groupby.length)
                ? groupby
                : this._archnodes_of_type('row').map(function (node) {
                      return node.attrs.name;
                  })
        });
        return this._fetch();
    },
    _fetch: function () {
        // ignore if view hasn't been loaded yet
        if (!this.fields_view || this.get('range') === undefined) {
            return;
        }
        var _this = this;
        // FIXME: since enqueue can drop functions, what should the semantics be for it to return a promise?
        this._enqueue(function () {
            _this._model.call(
                'read_grid', {
                    row_fields: _this.get('groupby'),
                    col_field: _this._col_field.name(),
                    cell_field: _this._cell_field.name(),
                    range: _this.get('range') || false,
                    domain: _this.get('domain') || [],
                    context: _this.get_full_context(),
                }).then(function (results) {
                    _this._navigation.set({
                        prev: results.prev,
                        next: results.next,
                    });
                    _this.set('grid_data', results);
                });
        });
    },
    _enqueue: function (fn) {
        // We only want a single fetch being performed at any time (because
        // there's really no point in performing 5 fetches concurrently just
        // because the user has just edited 5 records), utils.Mutex does that
        // fine, *however* we don't actually care about all the fetches, if
        // we're enqueuing fetch n while fetch n-1 is waiting, we can just
        // drop the older one, it's only going to delay the currently
        // useful and interesting job.
        //
        // So when requesting a fetch
        // * if there's no request waiting on the mutex (for a fetch to come
        //   back) set the new request waiting and queue up a fetch on the
        //   mutex
        // * if there is already a request waiting (and thus an enqueued fetch
        //   on the mutex) just replace the old request, so it'll get taken up
        //   by the enqueued fetch eventually
        var _this = this;
        if (this._in_waiting) {
            // if there's already a query waiting for a slot, drop it and replace
            // it by the new updated query
            this._in_waiting = fn;
        } else {
            // if there's no query waiting for a slot, add the current one and
            // enqueue a fetch job
            this._in_waiting = fn;
            this._fetch_mutex.exec(function () {
                var fn = _this._in_waiting;
                _this._in_waiting = null;

                return fn();
            })
        }

    },
    _archnodes_of_type: function (type) {
        return _.filter(this.fields_view.arch.children, function (c) {
            return c.tag === 'field' && c.attrs.type === type;
        });
    },
    _make_field: function (name, arch_f) {
        var descr = this.fields_view.fields[name];
        var Cls = fields[descr.type]
               || (arch_f && fields[arch_f.attrs.widget])
               || Field;

        return new Cls(name, descr, arch_f);
    },
    _fields_of_type: function (type) {
        return _(this._archnodes_of_type(type)).map(function (arch_f) {
            var name = arch_f.attrs.name;
            return this._make_field(name, arch_f);
        }.bind(this));
    },
    render_buttons: function ($node) {
        this._navigation = new Arrows(
            this,
            this.fields_view.arch.children
                .filter(function (c) { return c.tag === 'button'; })
                .map(function (c) { return c.attrs; })
        );
        this._navigation.appendTo($node);
    },

    adjust: function (cell, new_value) {
        var difference = new_value - cell.value;
        if (!difference) {
            // cell value was set to itself, don't hit the server
            return;
        }
        // convert row values to a domain, concat to action domain
        var domain = this.get('domain').concat(cell.row.domain);

        var column_name = this._col_field.name();
        return this._model.call('adjust_grid', {
            row_domain: domain,
            column_field: column_name,
            column_value: cell.col.values[column_name][0],
            cell_field: this._cell_field.name(),
            change: difference,
            context: this.get_full_context()
        }).then(this.proxy('_fetch'));
    },
});
core.view_registry.add('grid', GridView);

var Arrows = Widget.extend({
    template: 'grid.GridArrows',
    events: {
        'click .grid_arrow_previous': function (e) {
            e.stopPropagation();
            this.getParent().set('pagination_context', this.get('prev'));
        },
        'click .grid_arrow_next': function (e) {
            e.stopPropagation();
            this.getParent().set('pagination_context', this.get('next'));
        },
        'click .grid_arrow_range': function (e) {
            e.stopPropagation();
            var $target = $(e.target);
            if ($target.hasClass('active')) {
                return;
            }
            this._activate_range($target.data('name'));
        },
        'click .grid_arrow_button': function (e) {
            e.stopPropagation();
            var button = this._buttons[$(e.target).data('index')];
                this.getParent().get_ids().then(function (ids) {
                    this.getParent().do_execute_action(button, new data.DataSetStatic(
                    this,
                    this.getParent()._model.name,
                    this.getParent().get_full_context(button.context),
                    ids
                ));
            }.bind(this));
        }
    },
    init: function (parent, buttons) {
        this._super.apply(this, arguments);
        this._ranges = _(this.getParent()._col_field._arch.children).map(function (c) {
            return c.attrs;
        });
        this._buttons = buttons;
        this.on('change:prev', this, function (_, change) {
            this.$('.grid_arrow_previous').toggleClass('hidden', !change.newValue);
        });
        this.on('change:next', this, function (_, change) {
            this.$('.grid_arrow_next').toggleClass('hidden', !change.newValue);
        });
    },
    start: function () {
        var first_range = this._ranges[0];
        var range_name =
            this.getParent()._model.context().eval()['grid_range']
            || first_range && first_range.name;

        this._activate_range(range_name);
    },
    _activate_range: function (name) {
        var index, range = null;
        if (name) {
            index = _.findIndex(this._ranges, function (range) {
                return range.name === name;
            });
            range = index !== -1 ? this._ranges[index] : null;
        }
        this.getParent().set('range', range);

        if (!range) { return; }

        this.$('.grid_arrow_range')
                .eq(index).addClass('active')
                .siblings().removeClass('active');
    }
});
return {
    GridView: GridView,
}

});
