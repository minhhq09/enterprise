odoo.define('mobile.plugin', function (require) {
"use strict";


var core = require('web.core');
var mobile_utility = require('mobile.utility');

var DeviceUtility = false;
mobile_utility.Available = typeof OdooDeviceUtility != 'undefined';


/*
    Callback registry used for handling 'Deferred' callbacks from native mobile
    Why Deferred ?
    Because some native operation like get GPS location will take time.
*/
var Callbacks = {
    callback_registry: {},
    registerCallback: function(callbackId) {
        var def = $.Deferred();
        var callbackId = _.uniqueId("_om_" + new Date().getTime());
        def.callbackId = callbackId;
        this.callback_registry[callbackId] = {
            id: callbackId,
            successCallback: function(success) {
                def.resolve(success);
            },
            errorCallback: function(error) {
                def.reject(error);
            }
        };
        return def;
    },
    doCallback: function(callbackId, data) {
        var self= Callbacks;
        if (self.callback_registry.hasOwnProperty(callbackId)) {
            if (data.success) {
                self.callback_registry[callbackId].successCallback(data);
            } else {
                self.callback_registry[callbackId].errorCallback(data);
            }
        }
    }
}

if(mobile_utility.Available){
    // Detaching global variables 
    DeviceUtility = OdooDeviceUtility;
    OdooDeviceUtility = undefined;
    // Attaching callbacks
    window.doCallback = Callbacks.doCallback;
}


/*
    mobile.plugin will used for creating mobile plugins.
    these plugins can invoke methods in native mobile device.
    and these plugins can also get response in result.

    HOW TO CREATE MOBILE PLUGINS
    ============================
    // Take mobile plugin class
    var MobilePlugin = require( 'mobile.plugin' );

    // Extend this class to create new plugin
    MobilePlugin.extend({
        // Give plugin name is exact same plugin name created in native mobile
        plugin: "datetime",
        requestDatePicker: function(data){
            // Invoke method of plugin created in native mobile
            return this.invoke("requestDateTimePicker", data, true);
        }
    });

    HOW TO ADD METHOD IN PREVIOUSLY CREATED PLUGINS
    ===============================================
    Simply just create new plugin with same plugin name
    if you want to add new method in previously created datetime plugin
    MobilePlugin.extend({
        plugin: "datetime",
        newMetod: function(data){
            
        }
    });
    Note: if you give same method name then it will ignore that method

    HOW TO INVOKE METHOD
    ====================
    Two type of method you can invoke to native mobile from Java Script
    1) simple_action
        > used for such operation which are returns nothing (void)
        Like: Make Vibrate
        > used for such operation which are returns data without any waiting 
        Like: Get Device Model Name 
        Example,
        this.invoke("method_name", data_payload<TYPE JSON>);
    2) deferred_action
        > used for such operation which are returns Deferred response
        Like: Get GPS location
        (Once you invoke GPS, it is not known when response would come
         because system will ask user to turn on GPS if it is off)
        Example,
        this.invoke("method_name", data_payload<TYPE JSON>, true);
        here last parameter will indicate method has differed response

*/

var Plugin = core.Class.extend({
    invoke: function(method, data, DeferredCallback) {
        var action = _.str.sprintf("%s.%s", this.plugin, method);
        if(_.isUndefined(data)){
            data = {};
        }
        data = JSON.stringify(data);
        if (_.isUndefined(DeferredCallback)) {
            return this.simple_action(action, data);
        } else {
            return this.deferred_action(action, data);
        }
    },
    simple_action: function(action, data) {
        if (mobile_utility.Available) {
            return JSON.parse(DeviceUtility.execute(action, data, null))
        } else {
            return { 'error': 'Services available only on mobile' };
        }
    },
    deferred_action: function(action, data) {
        if (mobile_utility.Available) {
            var deferred = Callbacks.registerCallback();
            DeviceUtility.execute(action, data, deferred.callbackId);
            return deferred;
        } else {
            return $.Deferred().reject({ 'error': 'Services available only on mobile' });
        }
    }
});

var MobilePlugin = {
    extend: function(defination) {
        var plugin = Plugin.extend(defination);
        mobile_utility.add(plugin);
    }
}

return MobilePlugin;

});