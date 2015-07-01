odoo.define('web.CompanyLogo', function (require) {
"use strict";

var Widget = require('web.Widget');
var session = require('web.session');
var Model = require('web.Model');


var CompanyLogo = Widget.extend({
    template: 'CompanyLogo',
    events: {
        'click .oe_logo_edit_admin': 'logo_edit',
        'click .oe_logo img': 'on_logo_click',
    },
    start: function () {
        var res = this._super.apply(this, arguments);
        this.update_logo();
        return res;
    },
    update_logo: function() {
        var company = session.company_id;
        var img = session.url('/web/binary/company_logo' + '?db=' + session.db + (company ? '&company=' + company : ''));
        this.$('.oe_logo img').attr('src', '').attr('src', img);
        this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', session.uid === 1);
    },
    logo_edit: function(ev) {
        var self = this;
        ev.preventDefault();
        self.alive(new Model("res.users").get_func("read")(session.uid, ["company_id"])).then(function(res) {
            self.rpc("/web/action/load", { action_id: "base.action_res_company_form" }).done(function(result) {
                result.res_id = res.company_id[0];
                result.target = "new";
                result.views = [[false, 'form']];
                result.flags = {
                    action_buttons: true,
                    headless: true,
                };
                self.getParent().getParent().action_manager.do_action(result);
                var form = self.getParent().getParent().action_manager.dialog_widget.views.form.controller;
                form.on("on_button_cancel", self.getParent().getParent().action_manager, self.getParent().getParent().action_manager.dialog_stop);
                form.on('record_saved', self, function() {
                    self.getParent().getParent().action_manager.dialog_stop();
                    self.update_logo();
                });
            });
        });
        return false;
    },
});

return CompanyLogo;

});
