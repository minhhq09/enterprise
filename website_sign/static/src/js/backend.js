
odoo.define('website_sign.backend_iframe', function(require) {
    'use strict';

    var core = require('web.core');
    var IFrameWidget = require('web.IFrameWidget'); // FIXME ugly
    var ControlPanelMixin = require('web.ControlPanelMixin');

    var WIDGETS = {};

    WIDGETS.SignIFrameWidget = IFrameWidget.extend(ControlPanelMixin, {
        init: function(parent, options, cp_content) {
            if(!options.context.src) { // FIXME ugly
                window.location.href = '/web';
            }
            this._super(parent, options.context.src || '');
            this.cp_content = cp_content || {};
        },

        start: function() {
            var self = this;

            return self._super().then(function() {
                self.actionManager = self.getParent();
            });
        },

        bind_events: function() {
            this._super();

            if(this.el.contentDocument.location.href.slice(-this.url.length) !== this.url) {
                var action = this.getOnLeaveAction(this.el.contentDocument.location.href);
                var options = this.getOnLeaveOptions(this.el.contentDocument.location.href);
                if(action && !$.isEmptyObject(action)) {
                    this.do_action(action, options);
                    return false;
                }
            }
            
            var $mainContent = this.$el.contents().find('body main').detach();
            if($mainContent.length > 0)
                $mainContent.appendTo(this.$el.contents().find('body').html(''));

            var realContent = this.$el.contents();
            for(var components in this.cp_content) {
                this.cp_content[components].each((function() {
                    function fct(i, el) {
                        var $elem = $(el);
                        var eventComponent = realContent.find($elem.data('eventSelector')).first();
                        var hideComponent = realContent.find($elem.data('hideSelector')).add(eventComponent);

                        if(eventComponent.length > 0) {
                            $elem.toggleClass('selected', eventComponent.prop('checked') === true);
                            $elem.off('click').on('click', function(e) {
                                eventComponent.trigger('click');
                                $elem.toggleClass('selected', eventComponent.prop('checked') === true);
                            });
                        }
                        else if($elem.data('eventSelector') !== undefined)
                            $elem.hide();

                        if(hideComponent.length > 0)
                            hideComponent.hide();

                        $elem.children().each(fct);
                    }
                    return fct;
                })());
            }

            this.refresh_panel();
        },

        getOnLeaveAction: function(newURL) {
            return {};
        },

        getOnLeaveOptions: function(newURL) {
            return {
                additional_context: {src: newURL}
            };
        },

        do_show: function() {
            this._super();
            this.$el.attr('src', this.url);
        },

        refresh_panel: function() {
            this.update_control_panel({
                breadcrumbs: this.actionManager.get_breadcrumbs(),
                cp_content: this.cp_content
            });
        }
    });

    WIDGETS.DashboardIframe = WIDGETS.SignIFrameWidget.extend({
        init: function(parent) {
            var $toggleGroup = $('<div/>').addClass("btn-group btn-group-sm");

            var $toggleDropdown = $('<button/>', {'data-toggle': 'dropdown', 'type': 'button'}).addClass("btn btn-default dropdown-toggle");
            this.$dropdown = $('<ul/>', {'role': 'menu'}).addClass("dropdown-menu filters-menu");

            $toggleGroup.append($toggleDropdown);
            $toggleGroup.append(this.$dropdown);

            $toggleDropdown.html('<span class="fa fa-filter"/> Filters <span class="caret"></span>');
            this.$dropdown.append($('<li/>').append($('<a/>', {html: "Favorites Only"})).data({'eventSelector': "#show_favorites_toggle", 'hideSelector': "label[for='show_favorites_toggle']"}));
            this.$dropdown.append($('<li/>').addClass("divider"));
            this.$dropdown.append($('<li/>').append($('<a/>', {html: "Show Archives"})).data({'eventSelector': "#show_archives_toggle", 'hideSelector': "label[for='show_archives_toggle']"}));

            this._super(parent, {context: {src: '/sign'}}, {$searchview_buttons: $toggleGroup});
        },

        getOnLeaveAction: function(newURL) {
            return {
                type: "ir.actions.client",
                tag: 'website_sign.dashboard_item_template',
                name: "New Template"
            };
        },

        iframe_clicked: function(e) {
            if(e.button !== 0)
                return true;

            var $elem = $(e.target).closest('.sign_dashboard_item > a');
            if($elem.length > 0 && $elem.attr('href')) {
                e.preventDefault();

                this.do_action({
                    type: "ir.actions.client",
                    tag: 'website_sign.dashboard_item' + (($elem.attr('href').indexOf('template') >= 0)? '_template' : '_document'),
                    name: (($elem.attr('href').indexOf('template') >= 0)? "Template \"" : "Document \"") + $elem.find('.sign_dashboard_item_title').text() + "\"",
                    context: {
                        src: $elem.attr('href')
                    }
                });
            }
        }
    });

    WIDGETS.TemplateIframe = WIDGETS.SignIFrameWidget.extend({
        init: function(parent, options) {
            var sendButton = $('<button/>', {html: "Send"}).addClass('btn btn-primary btn-sm').data('eventSelector', '#send_template_button');
            var shareButton = $('<button/>', {html: "Share"}).addClass('btn btn-link btn-sm').data('eventSelector', '#share_template_button');

            this._super(parent, options, {
                $buttons: sendButton.add(shareButton)
            });
        },

        getOnLeaveAction: function(newURL) {
            if(newURL.indexOf('document') >= 0) {
                return {
                    type: "ir.actions.client",
                    tag: 'website_sign.dashboard_item_document',
                    name: "New Document"
                };
            }
            else {
                return {
                    type: "ir.actions.client",
                    tag: 'website_sign.dashboard_item_template',
                    name: "New Template"
                };
            }
        },
    });

    WIDGETS.DocumentIframe = WIDGETS.SignIFrameWidget.extend({
        init: function(parent, options) {
            var cancelButton = $('<button/>', {html: "Cancel Request"}).addClass('btn btn-default btn-sm').data('eventSelector', '#cancel_request_button');

            this._super(parent, options, {
                $buttons: cancelButton
            });
        },

        getOnLeaveAction: function(newURL) {
            if(newURL.indexOf('document') >= 0)
                return {};
            else {
                return {
                    type: "ir.actions.client",
                    tag: 'website_sign.dashboard',
                    name: 'Digital Signatures Documents'
                };
            }
        },

        getOnLeaveOptions: function(newURL) {
            return $.extend(this._super(newURL), {clear_breadcrumbs: true});
        },
    });

    core.action_registry.add('website_sign.dashboard', WIDGETS.DashboardIframe);

    core.action_registry.add('website_sign.dashboard_item_template', WIDGETS.TemplateIframe);
    core.action_registry.add('website_sign.dashboard_item_document', WIDGETS.DocumentIframe);
    
    return WIDGETS;
});
