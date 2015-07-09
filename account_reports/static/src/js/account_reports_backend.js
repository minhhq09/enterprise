odoo.define('account_reports.account_report_generic', function (require) {
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
    // Stores all the parameters of the action.
    init: function(parent, action) {
        var self = this;
        this.actionManager = parent;
        this.base_url = action.context.url;
        this.report_id = action.context.id ? parseInt(action.context.id, 10) : undefined;
        this.report_model = action.context.model;
        this.given_context = {};
        var url = this.base_url;
        if (action.context.context) {
            this.given_context = action.context.context
        }
        self._super(parent);
    },
    willStart: function () {
        return this.get_html();
    },
    // Sets the html of the page, then creates a report widget and sets it on the page.
    start: function() {
        this.$el.html(this.html);
        var report_widget = new ReportWidget(this.actionManager);
        report_widget.setElement(this.$el);
        report_widget.start(this.context);
        return this._super();
    },
    /* When the report has to be reloaded with a new context (the user has chosen new options).
       Fetches the html again with the new options then sets the report widget. */
    restart: function(given_context) {
        var self = this;
        this.given_context = given_context;
        return this.get_html().then(function() {
            self.$el.html(self.html);
            var report_widget = new ReportWidget(self.actionManager);
            report_widget.setElement(self.$el);
            report_widget.start(self.context);
        });
    },
    // Fetches the html
    get_html: function() {
        var self = this;
        var id = this.report_id ? [this.report_id] : [];
        return new Model(this.report_model).call('get_report_type', [id]).then(function (result) { // Get the report_type
            self.report_type = result;
            return new Model('account.report.context.common').call('get_context_name_by_report_model_json').then(function (result) { // Get the dictionnary context name -> report model
                self.context_model = new Model(JSON.parse(result)[self.report_model]);
                // Fetch the context_id or create one if none exist.
                // Look for a context with create_uid = current user (and with possibly a report_id)
                var domain = [['create_uid', '=', self.session.uid]];
                if (self.report_id) {
                    domain.push(['report_id', '=', parseInt(self.report_id, 10)]);
                }
                return self.context_model.query(['id'])
                .filter(domain).first().then(function (result) {
                    var post_function = function () { // Finally, actually get the html after giving the context.
                        return self.context_model.call('get_html', [self.context_id, self.given_context]).then(function (result) {
                            self.html = result;
                            return self.post_load();
                        });
                    };
                    if(result && result.length > 0 && (self.given_context.force_account || self.given_context.force_fy)) { // If some values have to be forced
                        // Delete the old context to create a new one with the forced values.
                        return self.context_model.call('unlink', [result.id]);
                        result = null;
                    }
                    // If no context is found (or it has been deleted above), create a new one
                    if(!result) {
                        var create_vals = {};
                        if (self.report_id) { // In some cases, a report_id needs to be given
                            create_vals.report_id = self.report_id;
                        }
                        if (self.given_context.force_account) { // Force the account in the new context
                            create_vals.unfolded_accounts = [(4, self.given_context.force_account)];
                        }
                        if (self.given_context.force_fy) { // Force the financial year in the new context
                            create_vals.force_fy = true;
                        }
                        return self.context_model.call('create', [create_vals]).then(function (result) { // Eventually, create the report
                            self.context_id = result;
                            return post_function();
                        })
                    }
                    else { // If the context was found, simply store its id
                        self.context_id = result.id;
                        return post_function();
                    }
                });
            });
        });
    },
    // Updates the control panel and render the elements that have yet to be rendered
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
    // Once the html is loaded, fetches the context, the company_id, the fy, if there is xml export available and the company ids and names.
    post_load: function() {
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
    },
    do_show: function() {
        this._super();
        this.update_cp();
    },
    render_buttons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("accountReports.buttons", {xml_export: this.xml_export}));
        this.$buttons.find('.o_account-widget-pdf').bind('click', function () {
            window.open(self.base_url + '?pdf', '_blank')
        });
        this.$buttons.find('.o_account-widget-xls').bind('click', function () {
            window.open(self.base_url + '?xls', '_blank')
        });
        this.$buttons.find('.o_account-widget-xml').bind('click', function () {
            // For xml exports, first check if the export can be done
            return new Model('account.financial.html.report.xml.export').call('check', [self.report_model, self.report_id]).then(function (check) {
                if (check === true) {
                    window.open(self.base_url + '?xml', '_blank')
                }
                else { // If it can't be done, show why.
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
        this.pager = '';
        return ''
    },
    render_searchview: function() {
        this.$searchview = '';
        return this.$searchview;
    },
    render_searchview_buttons: function() {
        var self = this;
        if (this.report_type == 'date_range_extended') {
            this.$searchview_buttons = '';
            return this.$searchview_buttons;
        }
        // Render the searchview buttons and bind them to the correct actions
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
            self.onChangeDateFilter(event); // First trigger the onchange
            $('.o_account_reports_datetimepicker input').each(function () { // Parse all the values of the date pickers
                $(this).val(formats.parse_value($(this).val(), {type: 'date'}));
            })
            var report_context = { // Create the context that will be given to the restart method
                date_filter: $(event.target).parents('li').data('value'),
                date_from: self.$searchview_buttons.find("input[name='date_from']").val(),
                date_to: self.$searchview_buttons.find("input[name='date_to']").val(),
            };
            if (self.date_filter_cmp != 'no_comparison') { // Add elements to the context if needed
                report_context.date_from_cmp = self.$searchview_buttons.find("input[name='date_from_cmp']").val();
                report_context.date_to_cmp = self.$searchview_buttons.find("input[name='date_to_cmp']").val();
            }
            self.restart(report_context); // Then restart the report
        });
        this.$searchview_buttons.find('.o_account_reports_one-filter-cmp').bind('click', function (event) { // Same for the comparison filter
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
        this.$searchview_buttons.find('.o_account_reports_one-filter-bool').bind('click', function (event) { // Same for the boolean filters
            var report_context = {};
            report_context[$(event.target).parents('li').data('value')] = !$(event.target).parents('li').hasClass('selected');
            self.restart(report_context);
        });
        if (this.context.multi_company) { // Same for th ecompany filter
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
        var l10n = core._t.database.parameters; // Get the localisation parameters
        var $datetimepickers = this.$searchview_buttons.find('.o_account_reports_datetimepicker');
        var options = { // Set the options for the datetimepickers
            language : moment.locale(),
            format : time.strftime_to_moment_format(l10n.date_format),
            icons: {
                date: "fa fa-calendar",
            },
            pickTime: false,
        }
        $datetimepickers.each(function () { // Start each datetimepicker
            $(this).datetimepicker(options);
            if($(this).data('default-value')) { // Set its default value if there is one
                $(this).data("DateTimePicker").setValue(moment($(this).data('default-value')));
            }
        })
        if (this.context.date_filter != 'custom') { // For each foldable element in the dropdowns
            this.toggle_filter(this.$useCustomDates, this.$CustomDates, false); // First toggle it so it is closed
            this.$dateFilter.bind('hidden.bs.dropdown', function () {self.toggle_filter(self.$useCustomDates, self.$CustomDates, false);}); // When closing the dropdown, also close the foldable element
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
