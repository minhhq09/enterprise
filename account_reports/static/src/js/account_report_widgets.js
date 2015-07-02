odoo.define('account_reports.ReportWidget', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var Model = require('web.Model');
var Session = require('web.session');
var time = require('web.time');

var QWeb = core.qweb;

var ReportWidget = Widget.extend({
    events: {
        "click *[data-toggle='dropdown']": 'toggleDropdown',
        'click': 'hideDropdown',
        'click .fa-pencil-square': 'clickPencil',
        'click .fa-pencil': 'clickPencil',
        'click .o_account_reports_foldable': 'fold',
        'click .o_account_reports_unfoldable': 'unfold',
        'click .saveFootNote': 'saveFootNote',
        'click span.aml': 'displayMoveLine',
        'click .fa-trash-o': 'rmContent',
        'click .closeSummary': 'rmContent',
        'click .o_account_reports_saved-summary > span': 'editSummary',
        "change *[name='date_filter']": 'onChangeDateFilter',
        "change *[name='date_filter_cmp']": 'onChangeCmpDateFilter',
        "change *[name='date_to']": 'onChangeCmpDateFilter',
        "change *[name='date_from']": 'onChangeCmpDateFilter',
        "change *[name='comparison']": 'onChangeComparison',
        "click input[name='summary']": 'onClickSummary',
        "click button.saveSummary": 'saveSummary',
        'click button.saveContent': 'saveContent',
        'click button#saveFootNote': 'saveFootNote',
        'click .o_account_reports_add-footnote': 'footnoteFromDropdown',
        'click .o_account_reports_to-graph': 'displayMoveLinesByAccountGraph',
    },
    hideDropdown: function(e) {
        this.$('.dropdown-menu').hide();
    },
    toggleDropdown: function(e) {
        e.stopPropagation();
        e.preventDefault();
        $(e.target).parents('.dropdown').find('.dropdown-menu').toggle();
    },
    saveFootNote: function(e) {
        self = this;
        var report_name = $(e.target).parents('#footnoteModal').siblings("div.o_account_reports_body").find('div.o_account_reports_page').attr("data-report-name");
        var context_id = $(e.target).parents('#footnoteModal').siblings("div.o_account_reports_body").find('div.o_account_reports_page').attr("data-context");
        var note = $("#note").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var contextModel = new Model(this.context_by_reportname[report_name]);
        return contextModel.call('get_next_footnote_number', [[parseInt(context_id, 10)]]).then(function (footNoteSeqNum) {
            self.curFootNoteTarget.after(QWeb.render("supFootNoteSeqNum", {footNoteSeqNum: footNoteSeqNum}));
            return contextModel.query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('add_footnote', [[parseInt(context.footnotes_manager_id[0], 10)], $("#type").val(), $("#target_id").val(), $("#column").val(), footNoteSeqNum, note]);
                $('#footnoteModal').find('form')[0].reset();
                $('#footnoteModal').modal('hide');
                $("div.o_account_reports_page").append(QWeb.render("savedFootNote", {num: footNoteSeqNum, note: note}));
            });
        });
    },
    onKeyPress: function(e) {
        if ((e.which === 70) && (e.ctrlKey || e.metaKey) && e.shiftKey) { // Fold all
            $(".o_account_reports_foldable").trigger('click');
        }
        else if ((e.which === 229) && (e.ctrlKey || e.metaKey) && e.shiftKey) { // Unfold all
            $(".o_account_reports_unfoldable").trigger('click');
        }
    },
    start: function() {
        var self = this;
        QWeb.add_template("/account_reports/static/src/xml/account_report_financial_line.xml");
        this.$('[data-toggle="tooltip"]').tooltip()
        this.curFootNoteTarget;
        var res = this._super.apply(this, arguments);;
        var report_name = window.$("div.o_account_reports_page").attr("data-report-name");
        Session.on('error', this, function(error){
            $('#report_error').modal('show');
        });
        var load_info = new Model('account.report.context.common').call('get_context_name_by_report_name_json').then(function (result) {
            self.context_by_reportname = JSON.parse(result);
        });
        $(window).on("keydown", this, this.onKeyPress);
        return $.when(res, load_info);
    },
    onClickSummary: function(e) {
        e.stopPropagation();
        $(e.target).parents("div.o_account_reports_summary").html(QWeb.render("editSummary"));
        this.$("textarea[name='summary']").focus();
    },
    saveSummary: function(e) {
        e.stopPropagation();
        var report_name = $(e.target).parents("div.o_account_reports_page").attr("data-report-name");
        var context_id = $(e.target).parents("div.o_account_reports_page").attr("data-context");
        var summary = this.$("textarea[name='summary']").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        if (summary != '')
            $(e.target).parents("div.o_account_reports_summary").html(QWeb.render("savedSummary", {summary : summary}));
        else
            $(e.target).parents("div.o_account_reports_summary").html(QWeb.render("addSummary"));
        return new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id, 10)], summary]);
    },
    footnoteFromDropdown: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        self.curFootNoteTarget = $(e.target).parents("div.dropdown").find("a:first");
        if(self.curFootNoteTarget.parents('div.dropdown').find('sup').length == 0) {
            var type = $(e.target).parents('tr').data('type');
            var target_id = $(e.target).parents('tr').data('id');
            var column = $(e.target).parents('td').index();
            $("#footnoteModal #type").val(type);
            $("#footnoteModal #target_id").val(target_id);
            $("#footnoteModal #column").val(column);
            $('#footnoteModal').on('hidden.bs.modal', function (e) {
                $(this).find('form')[0].reset();
            });
            $('#footnoteModal').modal('show');
        }
    },
    editSummary: function(e) {
        e.stopPropagation();
        e.preventDefault;
        var $el = $(e.target);
        var height = Math.max($el.height(), 100);
        var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
        var par = $el.parents("div.o_account_reports_summary")
        $el.parents("div.o_account_reports_summary").html(QWeb.render("editSummary", {summary: text}));
        par.find("textarea").height(height);
        this.$("textarea[name='summary']").focus();
    },
    clickPencil: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        if ($(e.target).parent().is('.o_account_reports_next-action')) {
            self.setNextAction(e);
        }
        else if ($(e.target).parents("div.o_account_reports_summary, p.footnote").length > 0) {
            var num = 0;
            if ($(e.target).parent().parent().is("p.footnote")) {
                $(e.target).parent().parent().attr('class', 'footnoteEdit')
                var $el = $(e.target).parent().parent().find('span.text');
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                text = text.split('.');
                var num = text[0];
                text = text[1];
                $el.html(QWeb.render("editContent", {num: num, text: text}));
            }
            else {
                var $el = $(e.target).parents('div.o_account_reports_saved-summary').children('span');
                var height = $el.height();
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                var par = $el.parent()
                $el.replaceWith(QWeb.render("editContent", {num: 0, text: text}));
                par.find("textarea").height(height);
            }
        }
        else if ($(e.target).parent().parent().find("sup").length == 0) {
            self.curFootNoteTarget = $(e.target).parent().parent();
            var type = $(e.target).parents('tr').data('type');
            var target_id = $(e.target).parents('tr').data('id');
            var column = $(e.target).parents('td').index();
            $("#footnoteModal #type").val(type);
            $("#footnoteModal #target_id").val(target_id);
            $("#footnoteModal #column").val(column);
            $('#footnoteModal').on('hidden.bs.modal', function (e) {
                $(this).find('form')[0].reset();
            });
            $('#footnoteModal').modal('show');
        }
    },
    saveContent: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.o_account_reports_page").attr("data-report-name");
        var context_id = $(e.target).parents("div.o_account_reports_page").attr("data-context");
        var text = $(e.target).siblings('textarea').val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var footNoteSeqNum = $(e.target).parents('p.footnoteEdit').text().split('.')[0];
        if ($(e.target).parents("p.footnoteEdit").length > 0) {
            $(e.target).parents("p.footnoteEdit").attr('class', 'footnote')
            $(e.target).siblings('textarea').replaceWith(text);
            new Model(this.context_by_reportname[report_name]).query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('edit_footnote', [[parseInt(context.footnotes_manager_id[0], 10)], parseInt(footNoteSeqNum, 10), text]);
            });
        }
        else {
            if (text != '')
                $(e.target).parents("div.o_account_reports_summary").html(QWeb.render("savedSummary", {summary : text}));
            else
                $(e.target).parents("div.o_account_reports_summary").html(QWeb.render("addSummary"));
            new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id, 10)], text]);
        }
        $(e.target).remove();
    },
    rmContent: function(e) {
        e.stopPropagation();
        e.preventDefault();
        if ($(e.target).parents("div.o_account_reports_summary").length > 0) {
            var report_name = $(e.target).parents("div.o_account_reports_page").attr("data-report-name");
            var context_id = $(e.target).parents("div.o_account_reports_page").attr("data-context");
            $(e.target).parent().parent().replaceWith(QWeb.render("addSummary"));
            new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id, 10)], '']);
        }
        else {
            var num = $(e.target).parent().parent().text().split('.')[0].replace(/ /g,'').replace(/\r?\n/g,'');
            this.$("sup b a:contains('" + num + "')").parents('sup').remove();
            $(e.target).parent().parent().remove();
            var report_name = window.$("div.o_account_reports_page").attr("data-report-name");
            var context_id = window.$("div.o_account_reports_page").attr("data-context");
            new Model(this.context_by_reportname[report_name]).query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('remove_footnote', [[parseInt(context.footnotes_manager_id[0], 10)], parseInt(num, 10)]);
            });
        }
    },
    fold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.o_account_reports_page").attr("data-report-name");
        var context_id = $(e.target).parents("div.o_account_reports_page").attr("data-context");
        var el;
        var $el;
        var $nextEls = $(e.target).parents('tr').nextAll();
        for (el in $nextEls) {
            $el = $($nextEls[el]).find("td span.o_account_reports_domain-line-1, td span.o_account_reports_domain-line-2, td span.o_account_reports_domain-line-3");
            if ($el.length == 0)
                break;
            else {
                $($el[0]).parents("tr").hide();
            }
        }
        var active_id = $(e.target).parents('tr').find('td.o_account_reports_foldable').data('id');
        $(e.target).parents('tr').find('td.o_account_reports_foldable').attr('class', 'o_account_reports_unfoldable ' + active_id)
        $(e.target).parents('tr').find('span.o_account_reports_foldable').replaceWith(QWeb.render("unfoldable", {lineId: active_id}));
        $(e.target).parents('tr').toggleClass('o_account_reports_unfolded');
        return new Model(this.context_by_reportname[report_name]).call('remove_line', [[parseInt(context_id, 10)], parseInt(active_id, 10)]);
    },
    unfold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var self = this;
        var report_name = window.$("div.o_account_reports_page").attr("data-report-name");
        var context_id = window.$("div.o_account_reports_page").attr("data-context");
        var active_id = $(e.target).parents('tr').find('td.o_account_reports_unfoldable').data('id');
        var contextObj = new Model(this.context_by_reportname[report_name]);
        return contextObj.call('add_line', [[parseInt(context_id, 10)], parseInt(active_id, 10)]).then(function (result) {
            var el;
            var $el;
            var $nextEls = $(e.target).parents('tr').nextAll();
            var isLoaded = false;
            for (el in $nextEls) {
                $el = $($nextEls[el]).find("td span.o_account_reports_domain-line-1, td span.o_account_reports_domain-line-2, td span.o_account_reports_domain-line-3");
                if ($el.length == 0)
                    break;
                else {
                    $($el[0]).parents("tr").show();
                    isLoaded = true;
                }
            }
            if (!isLoaded) {
                var $cursor = $(e.target).parents('tr');
                new Model('account.report.context.common').call('get_full_report_name_by_report_name', [report_name]).then(function (result) {
                    var reportObj = new Model(result);
                    var f = function (lines) {
                        new Model(self.context_by_reportname[report_name]).query(['all_entries', 'cash_basis'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            new Model(self.context_by_reportname[report_name]).call('get_columns_types', [[parseInt(context_id, 10)]]).then(function (types) {
                                var line;
                                lines.shift();
                                for (line in lines) {
                                    $cursor.after(QWeb.render("report_financial_line", {l: lines[line], context: context, types: types}));
                                    $cursor = $cursor.next();
                                }
                            });
                        });
                    };
                    if (report_name == 'financial_report') {
                        contextObj.query(['report_id'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            reportObj.call('get_lines', [[parseInt(context.report_id[0], 10)], parseInt(context_id, 10), parseInt(active_id, 10)]).then(f);
                        });
                    }
                    else {
                        reportObj.call('get_lines', [parseInt(context_id, 10), parseInt(active_id, 10)]).then(f);
                    }
                });
            }
            $(e.target).parents('tr').find('td.o_account_reports_unfoldable').attr('class', 'o_account_reports_foldable ' + active_id)
            $(e.target).parents('tr').find('span.o_account_reports_unfoldable').replaceWith(QWeb.render("foldable", {lineId: active_id}));
            $(e.target).parents('tr').toggleClass('o_account_reports_unfolded');
        });
    },
});

return ReportWidget;

});