odoo.define('mobile.web', function (require) {
"use strict";

var mobile_utility = require('mobile.utility');
var web_datepicker = require('web.datepicker');
var session = require('web.Session');
var form_relational = require('web.form_relational');
var notification_manager = require('web.notification').NotificationManager;
var common = require('web.form_common');
var core = require('web.core');
var UserMenu = require('web.UserMenu');
var crashManager = require('web.CrashManager');


/*
    Override odoo date-picker(bootstrap date-picker) to display mobile native date picker
    Because of it is better to show native mobile date-picker to improve usability of Application
    (Due to Mobile users are used to native date picker)
*/
web_datepicker.DateWidget.include({
    start: function(){
        this._super.apply(this, arguments);
        if(mobile_utility.Available){
            //  super will initiate bootstrap date-picker object which is not required in mobile application.
            if(this.picker){
                this.picker.destroy();
            }
            this.set_readonly(true);
            this.setup_mobile_picker();
        }
    },
    setup_mobile_picker: function(){
        var self = this;
        this.$el.on('click', function() {
            mobile_utility.datetime.requestDatePicker({
                'value': self.get_value(),
                'type': self.type_of_date
            })
            .then(function(response) {
                self.set_value(response.data);
                self.commit_value();
            });
        });
    }
});

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

session.include({
    get_file: function (options) {
        if(mobile_utility.Available){
            mobile_utility.file_manager.downloadFile(options);
            if (options.complete) { options.complete(); }
        }else{
            this._super.apply(this, arguments);
        }
    }
})

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

form_relational.FieldMany2One.include({
    render_editable: function(){
        var self = this;
        this._super.apply(this, arguments);
        if(mobile_utility.Available){
            this.$el.find('input').prop('disabled', true);
            $(this.$el).on('click', self.on_mobile_click);
        }
    },
    on_mobile_click:function(e){
        if(!$(e.target).hasClass('o_external_button')){
            this.do_invoke_mobile_dialog('');
        };
    },
    do_invoke_mobile_dialog: function(term){
        var self = this;
        this.get_search_result(term).done(function(result) {
            self._callback_actions = {}

            _.each(result, function(r, i){
                if(!r.hasOwnProperty('id')){
                    self._callback_actions[i] = r.action;
                    result[i]['action_id'] = i;
                }
            })
            mobile_utility.many2one.startFieldDialog({'records': result, 'label': self.string})
                .then(function(response){
                    if(response.data.action == 'search'){
                        self.do_invoke_mobile_dialog(response.data.term);
                    }
                    if(response.data.action == 'select'){
                        self.reinit_value(response.data.value.id);
                    }
                    if(response.data.action == 'action'){
                        self._callback_actions[response.data.value.action_id]();
                    }
                });
        });
    }
});


notification_manager.include({
    display:function(notification){
        mobile_utility.notify.vibrate({'duration': 100})
        return this._super.apply(this, arguments);
    }
})

// Hide the logout link in mobile
UserMenu.include({
    start:function(){
        if(mobile_utility.Available){
            this.$('a[data-menu="logout"]').addClass('hidden');
            this.$('a[data-menu="account"]').addClass('hidden');
            this.$('a[data-menu="switch_account"]').removeClass('hidden');
        }
        return this._super();
    },
    on_menu_switch_account:function(){
        mobile_utility.base.switchAccount();
    }
});

crashManager.include({
    rpc_error:function(error){
        if(mobile_utility.Available){
            mobile_utility.base.crashManager(error);
        }
        return this._super.apply(this, arguments);
    }
})

var ContactSync = common.FormWidget.extend({
    template: 'ContactSync',
    events: {
        'click': 'on_click',
        
    },
    start: function(){
        if(!mobile_utility.Available){
            $(this.$el).hide();
        }
        return this._super.apply(this, arguments);
    },
    on_click: function(){
        this.field_manager.dataset.read_index(['name', 'image', 'parent_id', 'phone', 'mobile', 'fax', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id','website','function', 'title'], {}).then(function(r) {
            mobile_utility.contacts.addContact(r);
        });
    },
});

core.form_tag_registry.add('contactsync', ContactSync);

});