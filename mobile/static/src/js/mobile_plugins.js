odoo.define('mobile.plugins', function (require) {
"use strict";

var MobilePlugin = require('mobile.plugin');


MobilePlugin.extend({
    plugin: "base",
    switchAccount: function(){
        return this.invoke("switchAccount");
    },
    crashManager: function(data){
        return this.invoke("crashManager", data);
    },
});

MobilePlugin.extend({
    plugin: "datetime",
    requestDatePicker: function(data){
        return this.invoke("requestDateTimePicker", data, true);
    }
});

MobilePlugin.extend({
    plugin: "file_manager",
    downloadFile: function(data){
        return this.invoke("downloadFile", data);
    }
});

MobilePlugin.extend({
    plugin: "many2one",
    startFieldDialog: function(data){
        return this.invoke("startFieldDialog", data, true);
    }
});

MobilePlugin.extend({
    plugin: "notify",
    vibrate: function(data){
        return this.invoke("vibrate", data);
    },
    showToast: function(data){
        return this.invoke("showToast", data);
    }
});

MobilePlugin.extend({
    plugin: "contacts",
    addContact: function(data){
        return this.invoke("addContact", data);
    }
});

});