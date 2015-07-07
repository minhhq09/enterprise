odoo.define('web.NotificationManager', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var _t = core._t;

var Notification = Widget.extend({
    template: 'Notification',
    events: {
        'click .o_close': function(e) {
            e.preventDefault();
            this.destroy();
        }
    },
    init: function() {
        this._super.apply(this, arguments);
        this.classes = "";
        this.title = _t('Message');
        this.text = '';
        this.sticky = false;
    },
    start: function() {
        this._super.apply(this, arguments);

        var self = this;
        this.$el.addClass(this.classes).animate({opacity: 1.0}, 500, "swing", function() {
            if(!self.sticky) {
                setTimeout(function() {
                    self.$el.animate({opacity: 0.0}, 500, "swing", function() {
                        self.destroy();
                    });
                }, 2500);
            }
        });
    },
    notify: function(title, text, sticky, classes) {
        this.classes = classes || "";
        this.title = title;
        this.text = text;
        this.sticky = !!sticky;
        this.appendTo(this.getParent().$el);
    },
    warn: function(title, text, sticky) {
        this.notify(title, text, sticky, 'o_error');
    }
});

var NotificationManager = Widget.extend({
    className: 'o_notification_manager',

    notify: function(title, text, sticky) {
        var notification = new Notification(this);
        notification.notify(title, text, sticky);
        return notification;
    },
    warn: function(title, text, sticky) {
        var notification = new Notification(this);
        notification.warn(title, text, sticky);
        return notification;
    }
});

return NotificationManager;

});
