odoo.define('account.ReportsBackend', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var formats = require('web.formats');
var Model = require('web.Model');
var Session = require('web.session');
var time = require('web.time');
var ControlPanelMixin = require('web.ControlPanelMixin');
var pager = require('web.Pager');
var ReportWidget = require('account_reports.ReportWidget');

var QWeb = core.qweb;

var account_report_generic = Widget.extend(ControlPanelMixin, {
    init: function(parent, action) {
        var self = this;
        this.action_id = action.id;
        this.actionManager = parent;
        this.base_url = action.context.url;
        this.report_id = action.context.id ? parseInt(action.context.id, 10) : undefined;
        this.report_model = action.context.model;
        this.given_context = {}
        var url = this.base_url;
        if (action.context.addUrl) {
            url += action.context.addUrl;
        }
        if (action.context.addActiveId) {
            url += action.context.active_id;
        }
        if (action.context.context) {
            this.given_context = action.context.context
        }
        self._super(parent);
    },
    restart: function(given_context) {
        var self = this;
        this.given_context = given_context;
        return this.willStart().then(function() {
            return self.start()
        });
    },
    willStart: function () {
        var self = this;
        var id = this.report_id ? [this.report_id] : [];
        return new Model(this.report_model).call('get_report_type', [id]).then(function (result) {
            self.report_type = result;
            return new Model('account.report.context.common').call('get_context_name_by_report_model_json').then(function (result) {
                self.context_model = new Model(JSON.parse(result)[self.report_model]);
                self.page = 1;
                // Fetching the context_id or creating one if none exist.
                var domain = [['create_uid', '=', self.session.uid]];
                if (self.report_id) {
                    domain.push(['report_id', '=', parseInt(self.report_id, 10)]);
                }
                return self.context_model.query(['id'])
                .filter(domain).first().then(function (result) {
                    var post_function = function () {
                        return self.context_model.call('get_html', [self.context_id, self.given_context]).then(function (result) {
                            self.html = result;
                            return self.post_load();
                        });
                    };
                    if(result && result.length > 1 && ((self.given_context.force_account && self.report_model == 'account.general.ledger') || self.given_context.force_fy)) {
                        // We need to delete the old context to create a new one with the forced values.
                        return self.context_model.call('unlink', [result.id]);
                        result = null;
                    }
                    if(!result) {
                        var create_vals = {};
                        if (self.report_model == 'account.financial.html.report') {
                            create_vals.report_id = self.report_id;
                        }
                        if (self.given_context.force_account && self.report_model == 'account.general.ledger') {
                            create_vals.unfolded_accounts = [(4, self.given_context.force_account)];
                        }
                        if (self.given_context.force_fy) {
                            create_vals.force_fy = true;
                        }
                        return self.context_model.call('create', [create_vals]).then(function (result) {
                            self.context_id = result;
                            return post_function();
                        })
                    }
                    else {
                        self.context_id = result.id;
                        return post_function();
                    }
                });
            });
        });
    },
    update_cp: function() {
        if (!this.$buttons) {
            this.render_buttons();
        }
        if (!this.$searchview_buttons) {
            this.render_searchview_buttons();
        }
        if (!this.$searchview) {
            this.render_searchview();
        }
        var status = {
            breadcrumbs: this.actionManager.get_breadcrumbs(),
            cp_content: {$buttons: this.$buttons, $searchview_buttons: this.$searchview_buttons, $pager: this.pager, $searchview: this.$searchview},
        };
        return this.update_control_panel(status);
    },
    post_load: function() {
        if (this.report_model == 'account.followup.report' && self.given_context.followup_all) {
            return this.update_cp();
        }
        else {
            var self = this;
            var fetched_context_model = self.context_model; // used if the context model that is used to fetch the required information for the control panel is not the same that the normal context model.
            var select = ['id', 'date_filter', 'date_filter_cmp', 'date_from', 'date_to', 'periods_number', 'date_from_cmp', 'date_to_cmp', 'cash_basis', 'all_entries', 'company_ids', 'multi_company'];
            if (this.report_model == 'account.followup.report' && this.base_url.search('all') > -1) {
                fetched_context_model = new Model('account.report.context.followup.all');
                select = ['id', 'valuenow', 'valuemax', 'percentage', 'partner_filter', 'last_page']
            }
            return fetched_context_model.query(select)
            .filter([['id', '=', self.context_id]]).first().then(function (context) {
                return new Model('res.users').query(['company_id'])
                .filter([['id', '=', self.session.uid]]).first().then(function (user) {
                    return new Model('res.company').query(['fiscalyear_last_day', 'fiscalyear_last_month'])
                    .filter([['id', '=', user.company_id[0]]]).first().then(function (fy) {
                        return new Model('account.financial.html.report.xml.export').call('is_xml_export_available', [self.report_model, self.report_id]).then(function (xml_export) {
                            return self.context_model.call('get_available_company_ids_and_names', [context.id]).then(function (available_companies) {
                                self.xml_export = xml_export;
                                self.fy = fy;
                                self.context = context;
                                self.context.available_companies = available_companies;
                                self.render_buttons();
                                self.render_searchview_buttons()
                                self.render_searchview()
                                self.render_pager()
                                return self.update_cp();
                            });
                        });
                    });
                });
            });
        }
    },
    start: function() {
        this.$el.html(this.html);
        this.$el.contents().click(this.outbound_link.bind(this));
        var report_widget = new ReportWidget();
        report_widget.setElement(this.$el);
        report_widget.start();
        return this._super();
    },
    do_show: function() {
        this._super();
        this.update_cp();
    },
    render_buttons: function() {
        var self = this;
        if (this.report_model == 'account.followup.report') {
            return '';
        }
        this.$buttons = $(QWeb.render("accountReports.buttons", {xml_export: this.xml_export}));
        this.$buttons.find('.o_account-widget-pdf').bind('click', function () {
            window.open(self.base_url + '?pdf', '_blank')
        });
        this.$buttons.find('.o_account-widget-xls').bind('click', function () {
            window.open(self.base_url + '?xls', '_blank')
        });
        this.$buttons.find('.o_account-widget-xml').bind('click', function () {
            return new Model('account.financial.html.report.xml.export').call('check', [self.report_model, self.report_id]).then(function (check) {
                if (check === true) {
                    window.open(self.base_url + '?xml', '_blank')
                }
                else {
                    if (!self.$errorModal) {
                        self.$errorModal = $(QWeb.render("accountReports.errorModal"));
                    }
                    self.$errorModal.find('#insert_error').text(check);
                    self.$errorModal.modal('show');
                }
            });
        });
        return this.$buttons;
    },
    toggle_filter: function (target, toggle, is_open) {
        target
            .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
            .toggleClass('o_open_menu', is_open);
        toggle.toggle(is_open);
    },
    render_pager: function() {
        var self = this;
        if (this.report_model == 'account.followup.report') {
            if (this.base_url.search('all') > -1) {
                this.pager = new pager(this, this.context.last_page, this.page, 1);
                this.pager.on('pager_changed', this, function (state) {
                    self.page = state.current_min;
                    self.$el.attr({src: encodeURIcomponent('/account/followup_report/all/page/' + self.page)});
                });
                return this.pager;
            }
        }
        this.pager = '';
        return ''
    },
    render_searchview: function() {
        if (this.report_model == 'account.followup.report') {
            if (this.base_url.search('all') > -1) {
                this.$searchview = $(QWeb.render("accountReports.followupProgressbar", {context: this.context}));
                return this.$searchview;
            }
        }
        this.$searchview = '';
        return this.$searchview;
    },
    render_searchview_buttons: function() {
        var self = this;
        if (this.report_model == 'account.followup.report') {
            if (this.base_url.search('all') > -1) {
                this.$searchview_buttons = $(QWeb.render("accountReports.followupSearchView", {context: this.context}));
                this.$partnerFilter = this.$searchview_buttons.siblings('.o_account_reports_date-filter');
                this.$searchview_buttons.find('.o_account_reports_one-filter').bind('click', function (event) {
                    var url = self.base_url + encodeURIcomponent('?partner_filter=' + $(event.target).parents('li').data('value'));
                    self.$el.attr({src: url});
                });
                return this.$searchview_buttons;
            }
            else {
                return '';
            }
        }
        if (this.report_type == 'date_range_extended') {
            return '';
        }
        this.$searchview_buttons = $(QWeb.render("accountReports.searchView", {report_type: this.report_type, context: this.context}));
        this.$dateFilter = this.$searchview_buttons.siblings('.o_account_reports_date-filter');
        this.$dateFilterCmp = this.$searchview_buttons.siblings('.o_account_reports_date-filter-cmp');
        this.$useCustomDates = this.$dateFilter.find('.o_account_reports_use-custom');
        this.$CustomDates = this.$dateFilter.find('.o_account_reports_custom-dates');
        this.$useCustomDates.bind('click', function () {self.toggle_filter(self.$useCustomDates, self.$CustomDates);});
        this.$usePreviousPeriod = this.$dateFilterCmp.find('.o_account_reports_use-previous-period');
        this.$previousPeriod = this.$dateFilterCmp.find('.o_account_reports_previous-period');
        this.$usePreviousPeriod.bind('click', function () {self.toggle_filter(self.$usePreviousPeriod, self.$previousPeriod);});
        this.$useSameLastYear = this.$dateFilterCmp.find('.o_account_reports_use-same-last-year');
        this.$SameLastYear = this.$dateFilterCmp.find('.o_account_reports_same-last-year');
        this.$useSameLastYear.bind('click', function () {self.toggle_filter(self.$useSameLastYear, self.$SameLastYear);});
        this.$useCustomCmp = this.$dateFilterCmp.find('.o_account_reports_use-custom-cmp');
        this.$CustomCmp = this.$dateFilterCmp.find('.o_account_reports_custom-cmp');
        this.$useCustomCmp.bind('click', function () {self.toggle_filter(self.$useCustomCmp, self.$CustomCmp);});
        this.$searchview_buttons.find('.o_account_reports_one-filter').bind('click', function (event) {
            self.onChangeDateFilter(event);
            $('.o_account_reports_datetimepicker input').each(function () {
                $(this).val(formats.parse_value($(this).val(), {type: 'date'}));
            })
            var report_context = {
                date_filter: $(event.target).parents('li').data('value'),
                date_from: self.$searchview_buttons.find("input[name='date_from']").val(),
                date_to: self.$searchview_buttons.find("input[name='date_to']").val(),
            };
            if (self.date_filter_cmp != 'no_comparison') {
                report_context.date_from_cmp = self.$searchview_buttons.find("input[name='date_from_cmp']").val();
                report_context.date_to_cmp = self.$searchview_buttons.find("input[name='date_to_cmp']").val();
            }
            self.restart(report_context);
        });
        this.$searchview_buttons.find('.o_account_reports_one-filter-cmp').bind('click', function (event) {
            self.onChangeCmpDateFilter(event);
            $('.o_account_reports_datetimepicker input').each(function () {
                $(this).val(formats.parse_value($(this).val(), {type: 'date'}));
            })
            var filter = $(event.target).parents('li').data('value');
            var report_context = {
                date_filter_cmp: filter,
                date_from_cmp: self.$searchview_buttons.find("input[name='date_from_cmp']").val(),
                date_to_cmp: self.$searchview_buttons.find("input[name='date_to_cmp']").val(),
            };
            if (filter == 'previous_period' || filter == 'same_last_year') {
                report_context.periods_number = $(event.target).siblings("input[name='periods_number']").val();
            }
            self.restart(report_context);
        });
        this.$searchview_buttons.find('.o_account_reports_one-filter-bool').bind('click', function (event) {
            var report_context = {};
            report_context[$(event.target).parents('li').data('value')] = !$(event.target).parents('li').hasClass('selected');
            self.restart(report_context);
        });
        if (this.context.multi_company) {
            this.$searchview_buttons.find('.o_account_reports_one-company').bind('click', function (event) {
                var report_context = {};
                var value = $(event.target).parents('li').data('value');
                if(self.context.company_ids.indexOf(value) === -1){
                    report_context.add_company_ids = value;
                }
                else {
                    report_context.remove_company_ids = value;
                }
                self.restart(report_context);
            });
        }
        this.$searchview_buttons.find('li').bind('click', function (event) {event.stopImmediatePropagation();});
        var l10n = core._t.database.parameters;
        var $datetimepickers = this.$searchview_buttons.find('.o_account_reports_datetimepicker');
        var options = {
            language : moment.locale(),
            format : time.strftime_to_moment_format(l10n.date_format),
            icons: {
                date: "fa fa-calendar",
            },
            pickTime: false,
        }
        $datetimepickers.each(function () {
            $(this).datetimepicker(options);
            if($(this).data('default-value')) {
                $(this).data("DateTimePicker").setValue(moment($(this).data('default-value')));
            }
        })
        if (this.context.date_filter != 'custom') {
            this.toggle_filter(this.$useCustomDates, this.$CustomDates, false);
            this.$dateFilter.bind('hidden.bs.dropdown', function () {self.toggle_filter(self.$useCustomDates, self.$CustomDates, false);});
        }
        if (this.context.date_filter_cmp != 'previous_period') {
            this.toggle_filter(this.$usePreviousPeriod, this.$previousPeriod, false);
            this.$dateFilterCmp.bind('hidden.bs.dropdown', function () {self.toggle_filter(self.$usePreviousPeriod, self.$previousPeriod, false);});
        }
        if (this.context.date_filter_cmp != 'same_last_year') {
            this.toggle_filter(this.$useSameLastYear, this.$SameLastYear, false);
            this.$dateFilterCmp.bind('hidden.bs.dropdown', function () {self.toggle_filter(self.$useSameLastYear, self.$SameLastYear, false);});
        }
        if (this.context.date_filter_cmp != 'custom') {
            this.toggle_filter(this.$useCustomCmp, this.$CustomCmp, false);
            this.$dateFilterCmp.bind('hidden.bs.dropdown', function () {self.toggle_filter(self.$useCustomCmp, self.$CustomCmp, false);});
        }
        return this.$searchview_buttons;
    },
    outbound_link: function(e) {
        if ($(e.target).is('.o_account_reports_web-action')) {
            var self = this
            var action_id = $(e.target).data('action-id');
            var action_name = $(e.target).data('action-name');
            var active_id = $(e.target).data('active-id');
            var res_model = $(e.target).data('res-model');
            var force_context = $(e.target).data('force-context');
            var additional_context = {}
            if (active_id) {
                additional_context = {active_id: active_id}
            }
            if (res_model && active_id) {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: res_model,
                    res_id: active_id,
                    views: [[false, 'form']],
                    target: 'current'
                });
            }
            if (!_.isUndefined(force_context)) {
                var context = {
                    date_filter: this.context.date_filter,
                    date_filter_cmp: this.context.date_filter_cmp,
                    date_from: self.report_type != 'no_date_range' ? this.context.date_from : 'none',
                    date_to: this.context.date_to,
                    periods_number: this.context.periods_number,
                    date_from_cmp: this.context.date_from_cmp,
                    date_to_cmp: this.context.date_to_cmp,
                    cash_basis: this.context.cash_basis,
                    all_entries: this.context.all_entries,
                };
                additional_context.context = context;
                additional_context.force_context = true;
            }
            if (action_name && !action_id) {
                var dataModel = new Model('ir.model.data');
                var res = action_name.split('.')
                return dataModel.call('get_object_reference', [res[0], res[1]]).then(function (result) {
                    return self.do_action(result[1], {additional_context: additional_context});
                });
            }
            this.do_action(action_id, {additional_context: additional_context});
        }
    },
    onChangeCmpDateFilter: function(event, fromDateFilter) {
        var filter_cmp = (_.isUndefined(fromDateFilter)) ? $(event.target).parents('li').data('value') : this.context.date_filter_cmp;
        var filter = !(_.isUndefined(fromDateFilter)) ? $(event.target).parents('li').data('value') : this.context.date_filter;
        var no_date_range = this.report_type == 'no_date_range';
        if (filter_cmp == 'previous_period' || filter_cmp == 'same_last_year') {
            var dtTo = !(_.isUndefined(fromDateFilter)) ? this.$searchview_buttons.find("input[name='date_to']").val() : this.context.date_to;
            dtTo = moment(dtTo).toDate();
            if (!no_date_range) {
                var dtFrom = !(_.isUndefined(fromDateFilter)) ? this.$searchview_buttons.find("input[name='date_from']").val() : this.context.date_from;;
                dtFrom = moment(dtFrom).toDate();
            }   
            if (filter_cmp == 'previous_period') {
                if (filter.search("quarter") > -1) {
                    var month = dtTo.getMonth()
                    dtTo.setMonth(dtTo.getMonth() - 2);
                    dtTo.setDate(0);
                    if (dtTo.getMonth() == month - 2) {
                        dtTo.setDate(0);
                    }
                    if (!no_date_range) {
                        dtFrom.setMonth(dtFrom.getMonth() - 3);
                    }
                }
                else if (filter.search("year") > -1) {
                    dtTo.setFullYear(dtTo.getFullYear() - 1);
                    if (!no_date_range) {
                        dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                    }
                }
                else if (filter.search("month") > -1) {
                    dtTo.setDate(0);
                    if (!no_date_range) {
                        dtFrom.setMonth(dtFrom.getMonth() - 1);
                    }
                }
                else if (no_date_range) {
                    var month = dtTo.getMonth()
                    dtTo.setMonth(month - 1);
                    if (dtTo.getMonth() == month) {
                        dtTo.setDate(0);
                    }
                }
                else {
                    var diff = dtTo.getTime() - dtFrom.getTime();
                    dtTo = dtFrom;
                    dtTo.setDate(dtFrom.getDate() - 1);
                    dtFrom = new Date(dtTo.getTime() - diff);
                }
            }
            else {
                dtTo.setFullYear(dtTo.getFullYear() - 1);
                if (!no_date_range) {
                    dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                }
            }
            if (!no_date_range) {
                this.$searchview_buttons.find("input[name='date_from_cmp']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dtFrom));
            }
            this.$searchview_buttons.find("input[name='date_to_cmp']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dtTo));
        }
    },
    onChangeDateFilter: function(event) {
        var self = this;
        var no_date_range = self.report_type == 'no_date_range';
        var today = new Date();
        switch($(event.target).parents('li').data('value')) {
            case 'today':
                var dt = new Date();
                self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                break;
            case 'last_month':
                var dt = new Date();
                dt.setDate(0); // Go to last day of last month (date to)
                self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(1); // and then first day of last month (date from)
                    self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
            case 'last_quarter':
                var dt = new Date();
                dt.setMonth((moment(dt).quarter() - 1) * 3); // Go to the first month of this quarter
                dt.setDate(0); // Then last day of last month (= last day of last quarter)
                self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(1);
                    dt.setMonth(dt.getMonth() - 2);
                    self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
            case 'last_year':
                if (today.getMonth() + 1 < self.fy.fiscalyear_last_month || (today.getMonth() + 1 == self.fy.fiscalyear_last_month && today.getDate() <= self.fy.fiscalyear_last_day)) {
                    var dt = new Date(today.getFullYear() - 1, self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0)    
                }
                else {
                    var dt = new Date(today.getFullYear(), self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0)
                }
                $("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(dt.getDate() + 1);
                    dt.setFullYear(dt.getFullYear() - 1)
                    self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
            case 'this_month':
                var dt = new Date();
                dt.setDate(1);
                self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                dt.setMonth(dt.getMonth() + 1);
                dt.setDate(0);
                self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                break;
            case 'this_year':
                if (today.getMonth() + 1 < self.fy.fiscalyear_last_month || (today.getMonth() + 1 == self.fy.fiscalyear_last_month && today.getDate() <= self.fy.fiscalyear_last_day)) {
                    var dt = new Date(today.getFullYear(), self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0)
                }
                else {
                    var dt = new Date(today.getFullYear() + 1, self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0)
                }
                self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(dt.getDate() + 1);
                    dt.setFullYear(dt.getFullYear() - 1);
                    self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
        }
        self.onChangeCmpDateFilter(event, true);
    },
});

core.action_registry.add("account_report_generic", account_report_generic);
return account_report_generic;
});
