odoo.define('web_enterprise.DebugManager', function (require) {
"use strict";

var core = require('web.core');
var WebClient = require('web.WebClient');


if (core.debug) {
    WebClient.include({
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // Override toggle_app_switcher to trigger an event to update the debug manager's state
                var toggle_app_switcher = self.toggle_app_switcher;
                self.toggle_app_switcher = function(display) {
                    toggle_app_switcher.apply(self, arguments);
                    if (display) {
                        core.bus.trigger('current_action_updated');
                    } else {
                        var action = self.action_manager.get_inner_action();
                        core.bus.trigger('current_action_updated', action.action_descr, action.widget);
                    }
                };
            });
        },
    });
}

});
