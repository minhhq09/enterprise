odoo.define('web_studio.studio_report_kanban', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var KanbanView = require('web_kanban.KanbanView');


var StudioReportKanbanView = KanbanView.extend({
    open_record: function(event) {
        var self = this;
        new Model('ir.actions.report.xml').call('studio_edit', [event.data.id]).then(function(action) {
            self.do_action(action);
        });
    },
});

core.view_registry.add('studio_report_kanban', StudioReportKanbanView);

return StudioReportKanbanView;

});
