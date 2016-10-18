odoo.define('web_studio.Menu', function (require) {
"use strict";

var Menu = require('web_enterprise.Menu');

var bus = require('web_studio.bus');
var EditMenu = require('web_studio.EditMenu');
var SubMenu = require('web_studio.SubMenu');
var SystrayItem = require('web_studio.SystrayItem');

Menu.include({
    events: _.extend({}, Menu.prototype.events, {
        'mouseenter .o_menu_sections > li:not(.open)': function(e) {
            if (this.studio_mode) {
                var $opened = this.$('.o_menu_sections > li.open');
                if($opened.length) {
                    $opened.removeClass('open');
                }
                $(e.currentTarget).addClass('open').find('> a').focus();
            }
        },
        'mouseleave .o_menu_sections': function() {
            if (this.studio_mode) {
                var $opened = this.$('.o_menu_sections > li.open');
                if($opened.length) {
                    $opened.removeClass('open');
                }
            }
        },
    }),

    init: function() {
        this._super.apply(this, arguments);
        bus.on('studio_toggled', this, function(studio_mode, action, active_view) {
            this.switch_studio_mode(studio_mode, action, active_view);
        });
        bus.on('studio_init', this, function(info) {
            this.dbuuid = info.dbuuid;
            this.multi_lang = info.multi_lang;
        });
    },

    switch_studio_mode: function(studio_mode, action, active_view) {
        if (this.studio_mode === studio_mode) {
            return;
        }

        var $main_navbar = this.$('.o_main_navbar');
        if (studio_mode) {
            if (!this.studio_mode) {
                this.$systray = $main_navbar
                    .find('.o_menu_systray')
                    .children(':not(".o_user_menu, .o_web_studio_navbar_item")')
                    .detach();
                this.$menu_toggle = $main_navbar.find('.o_menu_toggle').detach();
            }

            if (studio_mode === 'main') {
                var options = { multi_lang: this.multi_lang };
                this.studio_menu = new SubMenu(this, action, active_view, options);
                this.studio_menu.insertAfter($main_navbar);

                if (this.current_primary_menu) {
                    this.edit_menu = new EditMenu(this, this.menu_data, this.current_primary_menu);
                    this.edit_menu.appendTo($main_navbar.find('.o_menu_sections'));
                }

                // NOTES
                this.$notes = $('<div>')
                    .addClass('o_web_studio_notes')
                    .append($('<a>', {
                        href: 'http://pad.odoo.com/p/customization-' + this.dbuuid,
                        target: '_blank',
                        text: 'Notes',
                    }));
                this.$notes.insertAfter($main_navbar.find('.o_menu_systray'));
            }
        } else {
            if (this.edit_menu) {
                this.edit_menu.destroy();
                this.edit_menu = undefined;
            }
            if (this.studio_menu) {
                this.studio_menu.destroy();
                this.studio_menu = undefined;
            }
            if (this.$notes) {
                this.$notes.remove();
            }
            if (this.studio_mode) {
                this.$systray.prependTo('.o_menu_systray');
                this.$menu_toggle.prependTo('.o_main_navbar');
            }
        }

        this.studio_mode = studio_mode;
    },

    _on_secondary_menu_click: function() {
        if (this.studio_mode) {
            var systray_item = _.find(this.systray_menu.widgets, function(item) {
                return item instanceof SystrayItem;
            });
            systray_item.bump();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
