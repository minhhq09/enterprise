odoo.define('web.WebClient', function (require) {
"use strict";

var AbstractWebClient = require('web.AbstractWebClient');
var ActionManager = require('web.ActionManager');
var config = require('web.config');
var core = require('web.core');
var data_manager = require('web.data_manager');
var framework = require('web.framework');
var Model = require('web.DataModel');
var session = require('web.session');

var AppSwitcher = require('web_enterprise.AppSwitcher');
var Menu = require('web_enterprise.Menu');

return AbstractWebClient.extend({
    custom_events: _.extend({}, AbstractWebClient.prototype.custom_events, {
        app_clicked: 'on_app_clicked',
        menu_clicked: 'on_menu_clicked',
        scrollTo: 'scrollTo',
        show_app_switcher: function () {
            this.toggle_app_switcher(true);
        },
        hide_app_switcher: function () {
            // Restore the url
            $.bbq.pushState(this.url, 2); // merge_mode 2 to replace the current state
            this.toggle_app_switcher(false);
        },
    }),
    start: function () {
        this.$el.toggleClass('o_touch_device', config.device.touch);

        core.bus.on('change_menu_section', this, function (menu_id) {
            this.do_push_state(_.extend($.bbq.getState(), {
                menu_id: menu_id,
            }));
        });

        return this._super.apply(this, arguments);
    },
    bind_events: function () {
        var self = this;
        this._super.apply(this, arguments);

        /*
            Small patch to allow having a link with a href towards an anchor. Since odoo use hashtag 
            to represent the current state of the view, we can't easily distinguish between a link 
            towards an anchor and a link towards anoter view/state. If we want to navigate towards an 
            anchor, we must not change the hash of the url otherwise we will be redirected to the app 
            switcher instead.
            To check if we have an anchor, first check if we have an href attributes starting with #. 
            Try to find a element in the DOM using JQuery selector.
            If we have a match, it means that it is probably a link to an anchor, so we jump to that anchor.
        */
        this.$el.on('click', 'a', function(ev) {
            var disable_anchor = ev.target.attributes.disable_anchor;
            if (disable_anchor && disable_anchor.value === "true") {
                return;
            }

            var href = ev.target.attributes.href;
            if (href) {
                if (href.value[0] === '#' && href.value.length > 1) {
                    if (self.$("[id='"+href.value.substr(1)+"']").length) {
                        ev.preventDefault();
                        self.trigger_up('scrollTo', {'selector': href.value});
                    }
                }
            }
        });
    },
    show_application: function () {
        var self = this;
        this.set_title();

        var Menus = new Model('ir.ui.menu');
        return Menus.call('load_menus', [core.debug], {context: session.user_context}).then(function(menu_data) {
            // Compute action_id if not defined on a top menu item
            for (var i = 0; i < menu_data.children.length; i++) {
                var child = menu_data.children[i];
                if (child.action === false) {
                    while (child.children && child.children.length) {
                        child = child.children[0];
                        if (child.action) {
                            menu_data.children[i].action = child.action;
                            break;
                        }
                    }
                }
            }

            // Here, we instanciate every menu widgets and we immediately append them into dummy
            // document fragments, so that their `start` method are executed before inserting them
            // into the DOM.
            self.app_switcher = new AppSwitcher(self, menu_data);
            self.menu = new Menu(self, menu_data);

            var defs = [];
            defs.push(self.app_switcher.appendTo(document.createDocumentFragment()));
            defs.push(self.menu.prependTo(self.$el));
            return $.when.apply($, defs);
        }).then(function () {
            $(window).bind('hashchange', self.on_hashchange);

            // If the url's state is empty, we execute the user's home action if there is one (we
            // show the app switcher if not)
            // If it is not empty, we trigger a dummy hashchange event so that `self.on_hashchange`
            // will take care of toggling the app switcher and loading the action.
            if (_.isEmpty($.bbq.getState(true))) {
                return new Model("res.users").call("read", [session.uid, ["action_id"]]).then(function(data) {
                    if(data.action_id) {
                        return self.do_action(data.action_id[0]).then(function() {
                            self.toggle_app_switcher(false);
                            self.menu.change_menu_section(self.menu.action_id_to_primary_menu_id(data.action_id[0]));
                        });
                    } else {
                        self.toggle_app_switcher(true);
                    }
                });
            } else {
                $(window).trigger('hashchange');
            }
        });
    },
    set_action_manager: function () {
        this.action_manager = new ActionManager(this, {webclient: this});
        return this.action_manager.appendTo(this.$el);
    },
    // --------------------------------------------------------------
    // do_*
    // --------------------------------------------------------------
    /**
     * Extends do_action() to toggle the appswitcher off if the action isn't displayed in a dialog
     */
    do_action: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function(action) {
            if (self.menu.appswitcher_displayed && action.target !== 'new') {
                self.toggle_app_switcher(false);
            }
        });
    },
    do_push_state: function (state) {
        if (!state.menu_id && this.menu) {
            state.menu_id = this.menu.current_primary_menu;
        }
        this._super.apply(this, arguments);
    },
    // --------------------------------------------------------------
    // URL state handling
    // --------------------------------------------------------------
    on_hashchange: function(event) {
        if (!this._ignore_hashchange) {
            var self = this;
            var stringstate = event.getState(false);
            if (!_.isEqual(this._current_state, stringstate)) {
                var state = event.getState(true);
                if (state.action || (state.model && (state.view_type || state.id))) {
                    state._push_me = false;  // no need to push state back...
                    self.action_manager.do_load_state(state, !!this._current_state).then(function () {
                        if (state.menu_id) {
                            if (state.menu_id !== self.menu.current_primary_menu) {
                                core.bus.trigger('change_menu_section', state.menu_id);
                            }
                        } else {
                            var action = self.action_manager.get_inner_action();
                            if (action) {
                                var menu_id = self.menu.action_id_to_primary_menu_id(action.get_action_descr().id);
                                if (menu_id) {
                                    core.bus.trigger('change_menu_section', menu_id);
                                }
                            }
                        }
                        self.toggle_app_switcher(false);
                    });
                } else if (state.menu_id) {
                    var action_id = self.menu.menu_id_to_action_id(state.menu_id);
                    self.do_action(action_id, {clear_breadcrumbs: true}).then(function () {
                        core.bus.trigger('change_menu_section', state.menu_id);
                        self.toggle_app_switcher(false);
                    });
                } else {
                    self.toggle_app_switcher(true);
                }
            }
            this._current_state = stringstate;
        }
        this._ignore_hashchange = false;
    },
    // --------------------------------------------------------------
    // Menu handling
    // --------------------------------------------------------------
    on_app_clicked: function (ev) {
        var self = this;
        return this.menu_dm.add(data_manager.load_action(ev.data.action_id))
            .then(function (result) {
                return self.action_mutex.exec(function () {
                    var completed = $.Deferred();
                    $.when(self.do_action(result, {
                        clear_breadcrumbs: true,
                        action_menu_id: ev.data.menu_id,
                    })).fail(function () {
                        self.toggle_app_switcher(true);
                        completed.resolve();
                    }).done(function () {
                        core.bus.trigger('change_menu_section', ev.data.menu_id);
                        self.toggle_app_switcher(false);
                        completed.resolve();
                    });
                    setTimeout(function () {
                        completed.resolve();
                    }, 2000);
                    return completed;
                });
            });
    },
    on_menu_clicked: function (ev) {
        var self = this;
        return this.menu_dm.add(data_manager.load_action(ev.data.action_id))
            .then(function (result) {
                return self.action_mutex.exec(function () {
                    var completed = $.Deferred();
                    $.when(self.do_action(result, {
                        clear_breadcrumbs: true,
                        action_menu_id: ev.data.menu_id,
                    })).always(function () {
                        completed.resolve();
                    });

                    setTimeout(function () {
                        completed.resolve();
                    }, 2000);

                    return completed;
                });
            }).always(function () {
                self.$el.removeClass('o_mobile_menu_opened');
            });
    },
    toggle_app_switcher: function (display) {
        if (display === this.app_switcher_displayed) {
            return; // nothing to do (prevents erasing previously detached webclient content)
        }
        if (display) {
            var self = this;
            this.clear_uncommitted_changes().then(function() {
                // Save the current scroll position of the action_manager
                self.action_manager.set_scrollTop(self.get_scrollTop());

                // Detach the web_client contents
                var $to_detach = self.$el.contents()
                        .not(self.menu.$el)
                        .not('.o_loading')
                        .not('.o_chat_window')
                        .not('.o_notification_manager')
                        .not('.ui-autocomplete')
                        .not('.blockUI');
                self.$web_client_content = framework.detach([{widget: self.action_manager}], {$to_detach: $to_detach});

                // Attach the app_switcher
                framework.append(self.$el, [self.app_switcher.$el], {
                    in_DOM: true,
                    callbacks: [{widget: self.app_switcher}],                    
                });
                self.app_switcher_displayed = true;

                // Save and clear the url
                self.url = $.bbq.getState();
                self._ignore_hashchange = true;
                $.bbq.pushState('#home', 2); // merge_mode 2 to replace the current state
            });
        } else {
            framework.detach([{widget: this.app_switcher}]);
            framework.append(this.$el, [this.$web_client_content], {
                in_DOM: true,
                callbacks: [{widget: this.action_manager}],
            });
            this.app_switcher_displayed = false;
        }

        this.menu.toggle_mode(display, this.action_manager.get_inner_action() !== null);
    },
    // --------------------------------------------------------------
    // Scrolltop handling
    // --------------------------------------------------------------
    get_scrollTop: function () {
        if (config.device.size_class <= config.device.SIZES.XS) {
            return this.el.scrollTop;
        } else {
            return this.action_manager.el.scrollTop;
        }
    },
    /**
     * Scrolls the webclient to either a given offset or a target element
     * Must be called with: trigger_up('scrollTo', options)
     * @param {Integer} [options.offset] the number of pixels to scroll from top
     * @param {Integer} [options.offset_left] the number of pixels to scroll from left
     * @param {String} [options.selector] the selector of the target element to scroll to
     */
    scrollTo: function (ev) {
        var offset = {top: ev.data.offset, left: ev.data.offset_left || 0};
        var xs_device = config.device.size_class <= config.device.SIZES.XS;
        if (!offset.top) {
            offset = framework.getPosition(document.querySelector(ev.data.selector));
            if (!xs_device) {
                // Substract the position of the action_manager as it is the scrolling part
                offset.top -= framework.getPosition(this.action_manager.el).top;
            }
        }
        if (xs_device) {
            this.el.scrollTop = offset.top;
        } else {
            this.action_manager.el.scrollTop = offset.top;
        }
        this.action_manager.el.scrollLeft = offset.left;
    },
});

});
