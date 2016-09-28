odoo.define('web_studio.customize', function(require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var web_client = require('web.web_client');
var studio_bus = require('web_studio.bus');

// this is the id for the root menu of the current action
var current_menu_id = null;

core.bus.on('change_menu_section', null, function (id) {
    var menu_item = _.findWhere(web_client.menu_data.children, {id: id});
    current_menu_id = menu_item.id;
});

// this file should regroup all methods required to do a customization,
// so, basically all write/update/delete operations made in web_studio.

return {
    create_new_app: function(name, model_id, icon) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/create_new_menu', 'call', {
            name: name,
            model_id: model_id,
            is_app: true,
            icon: icon,
        });
    },

    create_new_menu: function(name, parent_id, model_id) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/create_new_menu', 'call', {
            name: name,
            model_id: model_id,
            parent_id: parent_id,
            menu_id: current_menu_id,
        });
    },

    edit_action: function(action, args) {
        var self = this;
        var def = $.Deferred();
        data_manager.invalidate();
        ajax.jsonRpc('/web_studio/edit_action', 'call', {
            action_type: action.type,
            action_id: action.id,
            args: args,
        }).then(function(result) {
            if (result !== true) {
                Dialog.alert(this, result);
                def.reject();
            } else {
                self._reload_action(action.id)
                    .then(def.resolve.bind(def))
                    .fail(def.reject.bind(def));
            }
        }).fail(def.reject.bind(def));
        return def;
    },

    set_another_view: function(action_id, view_mode, view_id) {
        var self = this;
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/set_another_view', 'call', {
            action_id: action_id,
            view_mode: view_mode,
            view_id: view_id,
        }).then(function() {
            return self._reload_action(action_id);
        });
    },

    // The point of this function is to receive a list of customize operations
    // to do. This is the "operations" variable.
    edit_view: function(view_id, studio_view_name, studio_view_arch, operations) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/edit_view', 'call', {
            view_id: view_id,
            studio_view_name: studio_view_name,
            studio_view_arch: studio_view_arch,
            operations: operations,
            menu_id: current_menu_id,
        });
    },

    // This is used when the view is edited with the XML editor: the whole arch
    // is replaced by a new one.
    edit_view_arch: function(view_id, view_arch) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/edit_view_arch', 'call', {
            view_id: view_id,
            view_arch: view_arch,
        });
    },

    get_studio_view_arch: function(model, view_type, view_id) {
        return ajax.jsonRpc('/web_studio/get_studio_view_arch', 'call', {
            model: model,
            view_type: view_type,
            view_id: view_id,
            menu_id: current_menu_id,
        });
    },

    _reload_action: function(action_id) {
        return data_manager.load_action(action_id).then(function(new_action) {
            studio_bus.trigger('action_changed', new_action);
            return new_action;
        });
    },
};

});
