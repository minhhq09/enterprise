odoo.define('mail.gcm', function (require) {
"use strict";

var mobile_utility = require('mobile.utility');
var MobilePlugin = require('mobile.plugin');
var session = require('web.session');
var Model = require('web.Model');

//Mobile Plugin for getting gcm key from device
MobilePlugin.extend({
    plugin:'gcm',
    get_gcm_key:function(data){
        return this.invoke("getGCMKey", data, true);
    }
});

//Send info only if client is mobile
if(mobile_utility.Available){
    session.rpc("/get_gcm_info", {}).then(function (data) {
        if(data.gcm_project_id){
            mobile_utility.gcm.get_gcm_key({'project_id': data.gcm_project_id, 'inbox_action': data.inbox_action}).then(function(response){
                if(response.success && data.subscription_ids.indexOf(response.data.subscription_id) == -1){
                    new Model("res.partner")
                        .call("add_device_identity", [[data.partner_id], response.data.subscription_id, response.data.device_name, 'gcm'])
                }
            });
        }
    });

}

// hide notification if user manually opened record

//Mobile Plugin
MobilePlugin.extend({
    plugin:'base',
    hashChange:function(data){
        return this.invoke("hashChange", data);
    }
});


var current_hash;
$(window).bind('hashchange', function(event){
    var hash = event.getState();
    if (!_.isEqual(current_hash, hash)) {
        mobile_utility.base.hashChange(hash);
    }
    current_hash = hash;
});

});
