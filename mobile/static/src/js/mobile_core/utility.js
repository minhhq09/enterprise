odoo.define('mobile.utility', function (require) {
"use strict";

var Registry = require('web.Registry');

/* 
    'mobile.utility' is used by odoo javascript to access methods to invoke native mobile operation
    created by various plugins.
    HOW TO USE
    ==========
    Example,
    var mobile_utility = require('mobile.utility');
                   <plugin> < plugin method > <json data you want to send to mobile>
    mobile_utility.datetime.requestDatePicker({'type': 'date','value': '12/05/1991'})

    Response will be json object or Differed object depend on your method
*/
var PluginRegistry = Registry.extend({
    init: function (mapping) {
        this.objs = Object.create(mapping || null);
        this._super();
    },
    get: function (key) {
        return this.objs[key];
    },
    add: function(plugin){
        this.register_plugin(plugin);
    },
    register_plugin: function(plugin){
        var plugin_name = plugin.prototype.plugin;
        if(this.contains(plugin_name)){
            var prototype = this.map[plugin_name].prototype;
            _.each(plugin.prototype, function(func, name) {
                if(prototype.hasOwnProperty(name) && typeof prototype[name] === 'function'){
                    console.warn(_.str.sprintf('Warning: Skipping "%s" method because it is already registered in plugin "%s"',name, plugin_name));
                }else{
                    prototype[name] = func;
                }
            });
            this.objs[plugin_name]= new this.map[plugin_name]();
        }else{
            this.map[plugin_name] = plugin;
            this.objs[plugin_name]= new plugin();
        }

        Object.defineProperty(this, plugin_name, {
            get: function() {
                return this.objs[plugin_name];
            },
            configurable: true
        });
    }
});

return new PluginRegistry();
});