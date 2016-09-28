odoo.define('web_studio.NewElementDialog', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var _t = core._t;

var NewElementDialog = Dialog.extend({
    template: 'web_studio.NewElementDialog',
    events: {
        'click td.o_web_studio_new_element': 'add_element',
    },
    init: function(parent, node, position) {
        var options = {
            title: _t('Add an Element'),
            size: 'medium',
            buttons: [
                {text: _t("Cancel"), close: true},
            ],
        };
        this.node = node;
        this.position = position;
        this._super(parent, options);
        this.$modal.addClass('o_web_studio');
    },
    add_element: function(event) {
        event.preventDefault();

        var self = this;
        var element = $(event.currentTarget).attr('data-element');
        var nodeClass = '.o_' + this.node.tag;
        var nodeIndex = $(event.currentTarget).closest(nodeClass)
            .prevAll().closest('.o_form_sheet > *').find(nodeClass).addBack(nodeClass)
            .length + 1;
        this.trigger_up('view_change', {
            type: 'add',
            structure: element,
            node: this.node,
            position: this.position,
            nodeIndex: nodeIndex,
            on_success: function() {
                self.close();
            },
        });
    },
});

return NewElementDialog;

});
