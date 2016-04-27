odoo.define('web_enterprise.AppSwitcher', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');
var Model = require('web.Model');
var utils = require('web.utils');

var QWeb = core.qweb;

var AppSwitcher = Widget.extend({
    template: 'AppSwitcher',
    events: {
        'click .o_action_app': 'on_app_click',
        'click .oe_instance_buy': 'enterprise_buy',
        'click .oe_instance_renew': 'enterprise_renew',
        'click .oe_instance_upsell': 'enterprise_upsell',
        'click a.oe_instance_register_show': function() {
            this.$('.oe_instance_register_form').slideToggle();
        },
        'click #confirm_enterprise_code': 'enterprise_code_submit',
        'click .oe_instance_hide_panel': 'enterprise_hide_panel',
        'input input': function(e) {
            if(!e.target.value) {
                this.reset_menu_display();
            } else {
                this.update(e.target.value);
            }
        },
        'click .o_menu_search_icon': function(e) {this.$input.focus();},
        'keydown': 'on_keydown',
    },
    init: function (parent, menu_data) {
        this._super.apply(this, arguments);
        this.menu_data = menu_data;
        this.lookup_list = [];
        this.menuitems_count = 0;
        this.mobile = config.device.size_class <= config.device.SIZES.XS;
        this._process_menu_data(menu_data, false, false);
    },
    willStart: function() {
        // Force the background image to be in the browser cache before the
        // stylesheet requests it
        var bg_loaded = $.Deferred();
        var bg = new Image();
        bg.onload = function () {
            bg_loaded.resolve();
        };
        bg.src = '/web_enterprise/static/src/img/application-switcher-bg.jpg';
        return $.when(this._super.apply(this, arguments), bg_loaded);
    },
    start: function () {
        var self = this;
        self.enterprise_expiration_check();
        this.$menu_search = this.$('.o_menu_search');
        this.$apps = this.$('.o_apps');
        this.$menuitems = this.$('.o_menuitems');
        this.$no_results = this.$('.o_no_results');
        this.$input = this.$('.o_menu_search input');
        this._link_dom_to_menuitems(this.menu_data);
        return this._super.apply(this, arguments);
    },
    /** Checks for the database expiration date and display a warning accordingly. */
    enterprise_expiration_check: function() {
        var self = this;
        if (!self.session) {
            return;
        }
        var P = new Model('ir.config_parameter');
        if (!odoo.db_info) {
            $.when(
                this.session.user_has_group('base.group_user'),
                this.session.user_has_group('base.group_system'),
                P.call('get_param', ['database.expiration_date']),
                P.call('get_param', ['database.enterprise_code']),
                P.call('get_param', ['database.expiration_reason'])
            ).then(function(is_user, is_admin, dbexpiration_date, dbenterprise_code, dbexpiration_reason) {
                // don't show the expiration warning for portal users
                if (!is_user) {
                    return;
                }
                var today = new moment();
                // if no date found, assume 1 month and hope for the best
                dbexpiration_date = new moment(dbexpiration_date || new moment().add(30, 'd'));
                var duration = moment.duration(dbexpiration_date.diff(today));
                var options = {
                    'diffDays': Math.round(duration.asDays()),
                    'dbexpiration_reason': dbexpiration_reason,
                    'warning': is_admin?'admin':(is_user?'user':false),
                    'dbenterprise_code': dbenterprise_code
                };
                self.enterprise_show_panel(options);
            });
        } else {
            $.when(
                P.call('get_param', ['database.enterprise_code'])
            ).then(function(dbenterprise_code) {
                // don't show the expiration warning for portal users
                if (!(odoo.db_info.warning))  {
                    return;
                }
                var today = new moment();
                // if no date found, assume 1 month and hope for the best
                var dbexpiration_date = new moment(odoo.db_info.expiration_date || new moment().add(30, 'd'));
                var duration = moment.duration(dbexpiration_date.diff(today));
                var options = {
                    'diffDays': Math.round(duration.asDays()),
                    'dbexpiration_reason': odoo.db_info.expiration_reason,
                    'warning': odoo.db_info.warning,
                    'dbenterprise_code': dbenterprise_code
                };
                self.enterprise_show_panel(options);
            });
        }
    },
    enterprise_show_panel: function(options) {
        //Show expiration panel 30 days before the expiry
        var self = this;
        var hide_cookie = utils.get_cookie('oe_instance_hide_panel');
        if ((options.diffDays <= 30 && !hide_cookie) || options.diffDays <= 0) {

            var expiration_panel = $(QWeb.render('WebClient.database_expiration_panel', {
                has_mail: _.includes(odoo._modules, 'mail'),
                diffDays: options.diffDays,
                dbenterprise_code:options.dbenterprise_code,
                dbexpiration_reason:options.dbexpiration_reason,
                warning: options.warning
            })).insertBefore(self.$menu_search);

            if (options.diffDays <= 0) {
                expiration_panel.children().addClass('alert-danger');
                expiration_panel.find('a.oe_instance_register_show').on('click.widget_events', self.events['click a.oe_instance_register_show']);
                expiration_panel.find('.oe_instance_buy').on('click.widget_events', self.proxy('enterprise_buy'));
                expiration_panel.find('.oe_instance_renew').on('click.widget_events', self.proxy('enterprise_renew'));
                expiration_panel.find('.oe_instance_upsell').on('click.widget_events', self.proxy('enterprise_upsell'));
                expiration_panel.find('#confirm_enterprise_code').on('click.widget_events', self.proxy('enterprise_code_submit'));
                expiration_panel.find('.oe_instance_hide_panel').hide();
                $.blockUI({message: expiration_panel.find('.database_expiration_panel')[0],
                           css: { cursor : 'auto' },
                           overlayCSS: { cursor : 'auto' } });
            }
        }
    },
    enterprise_hide_panel: function(ev) {
        ev.preventDefault();
        utils.set_cookie('oe_instance_hide_panel', true, 24*60*60);
        $('.database_expiration_panel').hide();
    },
    /** Save the registration code then triggers a ping to submit it*/
    enterprise_code_submit: function(ev) {
        ev.preventDefault();
        var enterprise_code = $('.database_expiration_panel').find('#enterprise_code').val();
        if (!enterprise_code) {
            var $c = $('#enterprise_code');
            $c.attr('placeholder', $c.attr('title')); // raise attention to input
            return;
        }
        var P = new Model('ir.config_parameter');
        var Publisher = new Model('publisher_warranty.contract');
        $.when(
            P.call('get_param', ['database.expiration_date']),
            P.call('set_param', ['database.enterprise_code', enterprise_code]))
        .then(function(old_date) {
            utils.set_cookie('oe_instance_hide_panel', '', -1);
            Publisher.call('update_notification', [[]]).then(function() {
                $.unblockUI();
                $.when(
                    P.call('get_param', ['database.expiration_date']),
                    P.call('get_param', ['database.expiration_reason']))
                .then(function(dbexpiration_date) {
                    $('.oe_instance_register').hide();
                    $('.database_expiration_panel .alert').removeClass('alert-info alert-warning alert-danger');
                    if (dbexpiration_date !== old_date) {
                        $('.oe_instance_hide_panel').show();
                        $('.database_expiration_panel .alert').addClass('alert-success');
                        $('.valid_date').html(moment(dbexpiration_date).format('LL'));
                        $('.oe_instance_success').show();
                    } else {
                        $('.database_expiration_panel .alert').addClass('alert-danger');
                        $('.oe_instance_error, .oe_instance_register_form').show();
                        $('#confirm_enterprise_code').html('Retry');
                    }
                });
            });
        });
    },
    enterprise_buy: function() {
        var limit_date = new moment().subtract(15, 'days').format("YYYY-MM-DD");
        new Model("res.users").call("search_count", [[["share", "=", false],["login_date", ">=", limit_date]]]).then(function(users) {
            window.location = $.param.querystring("https://www.odoo.com/odoo-enterprise/upgrade", {num_users: users});
        });
    },
    enterprise_renew: function() {
        new Model('ir.config_parameter').call('get_param', ['database.enterprise_code']).then(function(contract) {
            var params = contract ? {contract: contract} : {};
            window.location = $.param.querystring("https://www.odoo.com/odoo-enterprise/renew", params);
        });
    },
    enterprise_upsell: function() {
        var limit_date = new moment().subtract(15, 'days').format("YYYY-MM-DD");
        new Model('ir.config_parameter').call('get_param', ['database.enterprise_code']).then(function(contract) {
            new Model("res.users").call("search_count", [[["share", "=", false],["login_date", ">=", limit_date]]]).then(function(users) {
                var params = contract ? {contract: contract, num_users: users} : {num_users: users};
                window.location = $.param.querystring("https://www.odoo.com/odoo-enterprise/upsell", params);
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
    // Travel along the tree menu_data and push each node which has an action_id
    // into the list lookup_list. For each element to push:
    _process_menu_data: function (menu_data, parent, root_menu_id) {
        var self = this;
        _.each(menu_data, function (menu) {
            menu.path_name = parent ? [parent, menu.name].join(' / ') : menu.name;
            menu.root_menu_id = parent ? root_menu_id : menu.id;

            if (menu.action) {
                menu.action_id = menu.action.split(',').pop();
                menu.visible = !parent;
                menu.index = self.menuitems_count;
                self.menuitems_count = self.menuitems_count + 1;
                self.lookup_list.push(menu.path_name);
            }
            if (menu.children.length) {
                self._process_menu_data(menu.children, menu.path_name, menu.root_menu_id);
            }
        });
    },
    // Link on each menuitems on this.menu_data the related JQuery element
    // and the related JQuery group
    _link_dom_to_menuitems: function(menu_data) {
        var self = this;
        _.each(menu_data, function (menu) {
            if (menu.action_id) {
                menu.$el = self.$('.o_action_app[data-action-id=' + menu.action_id + ']');
                menu.$group = self.$('.o_secondary_menu_group[data-menu=' + menu.root_menu_id + ']');
            }
            if (menu.children.length) {
                self._link_dom_to_menuitems(menu.children);
            }
        });
    },
    // Compute the matching menuitems and applications matching the input
    // value, according to a fuzzy search. Set a boolean 'visible' to each link
    // that will be used by 'update_menuitems_render' to show/hide them
    update: function(search) {
        var self = this;
        // Make to fuzzy searches for the apps and the secondary menuitems
        var search_results = fuzzy.filter(search, this.lookup_list);
        var matching_elements_indexes = _.pluck(search_results, 'index');

        // Update the display
        this.$menuitems.find('.o_secondary_menu_group').addClass('o_menu_hidden');
        this.update_menu_data_visibility(this.menu_data, matching_elements_indexes);

        // Display 'No results' if needed
        var display_no_results = search_results.length === 0;
        this.$no_results.toggleClass('o_hidden', !display_no_results);

        // Fake a focus on the first element, pressing 'Enter' will
        // jump into it
        self.$('.o_action_app.o_focused').removeClass('o_focused');
        self.$('.o_action_app:visible:first()').addClass('o_focused');
    },
    update_menu_data_visibility: function(menu_data, matching_indexes) {
        var self = this; 
        _.each(menu_data, function(menu) {
            if (menu.action_id) {
                menu.visible = _.contains(matching_indexes, menu.index);
                menu.$el.toggleClass('o_menu_hidden', !menu.visible);
                if (menu.visible) {
                    menu.$group.removeClass('o_menu_hidden');
                }
            }
            if (menu.children.length) {
                self.update_menu_data_visibility(menu.children, matching_indexes);
            }
        });
    },
    // Reset the menuitems display at it initial state
    // All the apps displayed, no secondary menuitems and no group icon displayed
    reset_menu_display: function() {
        this.$apps.find('.o_app').removeClass('o_menu_hidden');
        this.$menuitems
            .find('.o_secondary_menu')
            .add('.o_secondary_menu_group')
            .addClass('o_menu_hidden');
        this.$no_results.addClass('o_hidden');
        if (!this.mobile) {
            this.$input.focus();
            this.$menu_search.addClass('o_bar_hidden');
        }
        this.$('.o_action_app.o_focused').removeClass('o_focused');
        this.$input.val('');
    },
    on_keydown: function (e) {
        this.$focused_element = $(document.activeElement);
        this.$visible_menuitems = this.$('.o_action_app:visible');
        this.is_focus_on_input = this.$focused_element.is('input');
        this.app_icon_by_line = config.device.size_class > config.device.SIZES.XS ? 6 : 4;
        this.visible_apps_count = this.$apps.find('.o_primary_menu:visible').length;
        this.visible_secondary_menu_count = this.$menuitems.find(".o_secondary_menu:visible").length;
        switch (e.which) {
            case $.ui.keyCode.DOWN:
                this.on_keydown_down(e);
                break;
            case $.ui.keyCode.RIGHT:
                this.on_keydown_right(e);
                break;
            case $.ui.keyCode.TAB:
                this.on_keydown_tab(e);
                break;
            case $.ui.keyCode.UP:
                this.on_keydown_up(e);
                break;
            case $.ui.keyCode.LEFT:
                this.on_keydown_left(e);
                break;
            case $.ui.keyCode.ENTER:
                this.on_keydown_enter(e);
                break;
            case $.ui.keyCode.PAGE_DOWN:
            case $.ui.keyCode.PAGE_UP:
                break;
            default:
                if (!this.mobile && this.$menu_search.hasClass('o_bar_hidden')) {
                    this.$menu_search.removeClass('o_bar_hidden');
                }
                if (!this.$focused_element.is('input') && !e.shiftKey) {
                    this.$input.focus();
                }
        }
    },
    on_keydown_down: function (e) {
        // Case fake focus on first menu
        if (this.is_focus_on_input && this.$visible_menuitems.first().hasClass('o_focused')) {
            this.$visible_menuitems.first().removeClass('o_focused');
            this.$visible_menuitems.first().focus();
            this.is_focus_on_input = false;
            this.$focused_element = this.$visible_menuitems.first();
        } else if (this.is_focus_on_input) {
            this.$visible_menuitems.first().focus();
            return;
        }
        var new_index = -1;
        var i = this.$visible_menuitems.index(this.$focused_element);
        if (this.$focused_element.hasClass('o_primary_menu')) {
            new_index = i + this.app_icon_by_line;
            if(new_index + 1 > this.visible_apps_count) {
                var app_lines_count = Math.ceil(this.visible_apps_count/this.app_icon_by_line);
                var current_line_number = Math.ceil(i+1/this.app_icon_by_line);
                if (app_lines_count > current_line_number) {
                    new_index = this.visible_apps_count - 1;                                
                } else {
                    if (!this.visible_secondary_menu_count) {
                        new_index = -1;
                    } else {
                        new_index = this.visible_apps_count;
                    }
                }
            }
        } else {
            new_index = i + 1;
            if(new_index >= this.$visible_menuitems.length) {
                new_index = -1;
            }
        }
        new_index === -1 ? this.$input.focus() : this.$visible_menuitems.eq(new_index).focus();
        e.preventDefault();
    },
    on_keydown_up: function (e) {
        // Case fake focus on first menu
        if (this.is_focus_on_input) {
            this.$visible_menuitems.first().removeClass('o_focused');
            this.$visible_menuitems.last().focus();
            return;
        }
        var i = this.$visible_menuitems.index(this.$focused_element);
        var new_index = -1;
        if (this.$focused_element.hasClass('o_primary_menu')) {
            new_index = Math.max(i - this.app_icon_by_line, -1);
        } else {
            new_index = i - 1;
        }
        new_index === -1 ? this.$input.focus() : this.$visible_menuitems.eq(new_index).focus();
        e.preventDefault();
    },
    on_keydown_right: function (e) {
        var self = this;
        // Case fake focus on first menu
        if (this.is_focus_on_input && this.$visible_menuitems.first().hasClass('o_focused') && this.$visible_menuitems.eq(1).hasClass('o_primary_menu')) {
            self.$visible_menuitems.first().removeClass('o_focused');
            self.$visible_menuitems.eq(1).focus();
            return; 
        } 
        var i = this.$visible_menuitems.index(this.$focused_element);
        if (this.$focused_element.hasClass('o_primary_menu')) {
            var new_index = i + 1;
            if (Math.floor(new_index/self.app_icon_by_line) === Math.floor(i/self.app_icon_by_line) && self.$visible_menuitems.eq(new_index).hasClass('o_primary_menu')) {
                self.$visible_menuitems.eq(new_index).focus();
                return;
            }
        }
    },
    on_keydown_left: function (e) {
        var self = this;
        // Case fake focus on first menu
        if (this.is_focus_on_input && this.$visible_menuitems.first().hasClass('o_focused')) {
            self.$visible_menuitems.first().removeClass('o_focused');
            self.$visible_menuitems.first().focus();
            return; 
        } 
        var i = this.$visible_menuitems.index(this.$focused_element);
        if (this.$focused_element.hasClass('o_primary_menu')) {
            var new_index = i - 1;
            if (Math.floor(new_index/self.app_icon_by_line) === Math.floor(i/self.app_icon_by_line)) {
                self.$visible_menuitems.eq(new_index).focus();
                return;
            }
        }
    },
    on_keydown_tab: function (e) {
        var self = this;
        if (this.is_focus_on_input) {
            if (self.$visible_menuitems.first().hasClass('o_focused')) {
                self.$visible_menuitems.first().removeClass('o_focused');
                self.$visible_menuitems.eq(1).focus();
            } else {
                e.shiftKey ? $(self.$visible_menuitems.slice(-1)[0]).focus() : self.$visible_menuitems.first().focus();
            }
        } else {
            var i = this.$visible_menuitems.index(this.$focused_element);
            if (e.shiftKey) {
                i === 0 ? self.$input.focus() : self.$visible_menuitems.eq(i-1).focus();
            } else {
                i === self.$visible_menuitems.length - 1 ? self.$input.focus() : self.$visible_menuitems.eq(i+1).focus();
            }
        }
        e.preventDefault();
    },
    on_keydown_enter: function (e) {
        if (this.is_focus_on_input) {
            this.$visible_menuitems.first().trigger('click');
        }
    },
});

return AppSwitcher;

});
