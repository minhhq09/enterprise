odoo.define('mail.fcm', function (require) {
"use strict";

var mobile_utility = require('mobile.utility');
var MobilePlugin = require('mobile.plugin');
var session = require('web.session');
var Model = require('web.Model');

//Mobile Plugin for getting fcm key from device
MobilePlugin.extend({
    plugin:'fcm',
    get_fcm_key:function(data){
        return this.invoke("getFCMKey", data, true);
    }
});

//Send info only if client is mobile
if(mobile_utility.Available){
    session.rpc("/get_fcm_info", {}).then(function (data) {
        if(data.fcm_project_id){
            mobile_utility.fcm.get_fcm_key({'project_id': data.fcm_project_id, 'inbox_action': data.inbox_action}).then(function(response){
                if(response.success && data.subscription_ids.indexOf(response.data.subscription_id) == -1){
                    new Model("res.partner")
                        .call("add_device_identity", [[data.partner_id], response.data.subscription_id, response.data.device_name, 'fcm'])
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
