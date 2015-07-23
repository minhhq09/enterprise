odoo.define('web.AppSwitcher', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var UserMenu = require('web.UserMenu');

var AppSwitcher = Widget.extend({
    template: 'AppSwitcher',
    events: {
        'click .o_app': 'on_app_click',
    },
    init: function (parent, menu_data) {
        this._super.apply(this, arguments);
        this.menu_data = menu_data;

        // Compute action_id if not defined on a top menu item
        for (var i = 0; i < this.menu_data.children.length; i++) {
            var child = this.menu_data.children[i];
            if (child.action === false) {
                while (child.children && child.children.length) {
                    child = child.children[0];
                    if (child.action) {
                        this.menu_data.children[i].action = child.action;
                        break;
                    }
                }
            }
        }
    },
    start: function () {
        var res = this._super.apply(this, arguments);

        // Force the background image to be in the browser cache before the
        // stylesheet requests it
        var bg = new Image();
        bg.onload = function () {
            return res;
        }
        bg.src = '/web/static/src/img/application-switcher-bg.jpg';
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
    init: function (parent) {
        this._super.apply(this, arguments);
        this.backbutton_displayed = false;
    },
    start: function () {
        var self = this;
        // Hide the app switcher when pressing the escape key
        core.bus.on('keyup', this, function (ev) {
            if (ev.keyCode == 27 && this.backbutton_displayed === true) {
                this.trigger_up('hide_app_switcher');
            }
        });

        var user_menu = new UserMenu(this);
        return this._super.apply(this, arguments).then(function () {
            user_menu.appendTo(self.$('.o_appswitcher_navbar_systray'));
        });
    },
    toggle_back_button: function (display) {
        this.$('.o_back_button').toggleClass('hidden', display);
        this.backbutton_displayed = !display;
    },
});

return {
    AppSwitcher: AppSwitcher,
    AppSwitcherNavbar: AppSwitcherNavbar,
};

});
