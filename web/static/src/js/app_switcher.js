odoo.define('web.AppSwitcher', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var UserMenu = require('web.UserMenu');
var Model = require('web.Model');
var QWeb = core.qweb;

var AppSwitcher = Widget.extend({
    template: 'AppSwitcher',
    events: {
        'click .o_action_app': 'on_app_click',
        'click .oe_instance_buy': 'enterprise_buy',
        'click .oe_instance_renew': 'enterprise_renew',
        'click .oe_instance_upsell': 'enterprise_upsell',
        'click a.oe_instance_register_show': function(ev) {$('.oe_instance_register_form').slideToggle();},
        'click #confirm_enterprise_code': 'enterprise_code_submit',
    },
    init: function (parent, menu_data) {
        this._super.apply(this, arguments);
        this.menu_data = menu_data;
    },
    willStart: function() {
        // Force the background image to be in the browser cache before the
        // stylesheet requests it
        var bg_loaded = $.Deferred();
        var bg = new Image();
        bg.onload = function () {
            bg_loaded.resolve();
        };
        bg.src = '/web/static/src/img/application-switcher-bg.jpg';

        return $.when(this._super.apply(this, arguments), bg_loaded);
    },
    start: function () {
        var self = this;
        self.enterprise_expiration_check();
        return this._super.apply(this, arguments);
    },
    /** Checks for the database expiration date and display a warning accordingly. */
    enterprise_expiration_check: function() {
        var self = this;
        if (!self.session) {
            return;
        }
        var P = new Model('ir.config_parameter');

        $.when(
            this.session.user_has_group('base.group_user'),
            P.call('get_param', ['database.expiration_date']),
            P.call('get_param', ['database.enterprise_code']),
            P.call('get_param', ['database.expiration_reason'])
        ).then(function(is_user, dbexpiration_date, dbenterprise_code, dbexpiration_reason) {
            // don't show the expiration warning for portal users
            if (!is_user || !dbexpiration_date) {
                return;
            }
            var today = new moment();
            dbexpiration_date = new moment(dbexpiration_date);
            var duration = moment.duration(dbexpiration_date.diff(today));
            var diffDays = Math.round(duration.asDays());

            //Show expiration panel 30 days before the expiry
            if (diffDays <= 30) {

                var expiration_panel = $(QWeb.render('WebClient.database_expiration_panel', {
                    diffDays: diffDays, dbenterprise_code:dbenterprise_code, dbexpiration_reason:dbexpiration_reason
                })).prependTo(self.$('.o_apps'));

                if (diffDays <= 0) {
                    expiration_panel.children().addClass('alert-danger');
                    expiration_panel.find('a.oe_instance_register_show').on('click', self.events['click a.oe_instance_register_show']);
                    $.blockUI({ message: expiration_panel[0] });
                }

            }
        });
    },
    /** Save the registration code then triggers a ping to submit it*/
    enterprise_code_submit: function(ev) {
        ev.preventDefault();
        var P = new Model('ir.config_parameter');
        var Publisher = new Model('publisher_warranty.contract');
        var enterprise_code = $('.database_expiration_panel').find('#enterprise_code').val();
        $.when(P.call('set_param', ['database.enterprise_code', enterprise_code])).then(function() {
            Publisher.call('update_notification', [[]]);
            $.unblockUI();
            location.reload();
        });
    },
    enterprise_buy: function(ev) {
        var limit_date = new moment().subtract(15, 'days').format("YYYY-MM-DD");
        new Model("res.users").call("search_count", [[["share", "=", false],["login_date", ">=", limit_date]]]).then(function(users) {
            window.location = "https://www.odoo.com/odoo-enterprise/upgrade?num_users=" + users;
        });
    },
    enterprise_renew: function(ev) {
        new Model('ir.config_parameter').call('get_param', ['database.enterprise_code']).then(function(code) {
            window.location = "https://www.odoo.com/odoo-enterprise/renew?code=" + code;
        });
    },
    enterprise_upsell: function(ev) {
        var limit_date = new moment().subtract(15, 'days').format("YYYY-MM-DD");
        new Model('ir.config_parameter').call('get_param', ['database.enterprise_code']).then(function(code) {
            new Model("res.users").call("search_count", [[["share", "=", false],["login_date", ">=", limit_date]]]).then(function(users) {
                window.location = "https://www.odoo.com/odoo-enterprise/upsell?num_users=" + users + "&code=" + code;
            });
        });
    },
    on_app_click: function (ev) {
        ev.preventDefault();
        this.trigger_up('app_clicked', {
            menu_id: $(ev.currentTarget).data('menu'),
            action_id: $(ev.currentTarget).data('action-id'),
        });
    },
});

var AppSwitcherNavbar = Widget.extend({
    template: 'AppSwitcherNavbar',
    events: {
        'click .o_back_button': function (ev) {
            ev.preventDefault();
            this.trigger_up('hide_app_switcher');
        }
    },
    on_attach_callback: function(options) {
        this.toggle_back_button(options && options.display_back_button);
        // Hide the app switcher when pressing the escape key
        core.bus.on('keyup', this, this._hide_app_switcher);
    },
    on_detach_callback: function() {
        // Unbind the event handler when the navbar is detached from the DOM
        core.bus.off('keyup', this, this._hide_app_switcher);
    },
    init: function () {
        this._super.apply(this, arguments);
        this.backbutton_displayed = false;
    },
    start: function () {
        var self = this;
        var user_menu = new UserMenu(this);
        return this._super.apply(this, arguments).then(function () {
            user_menu.appendTo(self.$('.o_appswitcher_navbar_systray'));
        });
    },
    toggle_back_button: function (display) {
        this.$('.o_back_button').toggleClass('hidden', !display);
        this.backbutton_displayed = display;
    },
    _hide_app_switcher: function (ev) {
        if (ev.keyCode === 27 && this.backbutton_displayed === true) {
            this.trigger_up('hide_app_switcher');
        }
    },
});

return {
    AppSwitcher: AppSwitcher,
    AppSwitcherNavbar: AppSwitcherNavbar,
};

});
