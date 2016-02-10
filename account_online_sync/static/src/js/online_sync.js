odoo.define('account_online_sync.acc_config_widget', function(require) {
"use strict";

var core = require('web.core');
var form_relational = require('web.form_relational');
var common = require('web.form_common');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var framework = require('web.framework');
var time = require('web.time');
var datepicker = require('web.datepicker');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var _t = core._t;

/**
 * Widget that will serve as base for plaid and yodlee widget, this widget can not work alone!
 * This widget create a dialog to allow user to configure an online account with yodlee or plaid interface
 */
// var OnlineSynchAccountConfigurationWidget = form_relational.FieldMany2One.extend({
var OnlineSynchAccountConfigurationWidget = Widget.extend({

    post_process_connection_result: function(resp_json) {
        var self = this;
        this.config_template = 'OnlineSynchLoginTemplate';
        //Must be implemented by children widget
        this.config_template_data = {}
    },

    bind_button: function() {
        var self = this;
        this.$('.js_process_next_step').click(function(){
            self.hide_error(); self.process_next_step();
        });
        this.$('.js_process_mfa_step').click(function(){
            self.hide_error(); self.process_mfa_step();
        });
        this.$('.js_conclude_configuration').click(function(){
            self.hide_error(); self.complete_process();
        });
        this.$('.js_process_cancel').click(function(){
            if (self.is_modal){
                self.$el.parents('.modal').modal('hide');
            }
        });
    },

    check_empty_field: function() {
        var self = this;
        var $inputs = this.$el.find('input[optional="false"]:not([type="radio"])');
        var $radios = this.$el.find('input[type="radio"]');
        var $selects = this.$el.find('select');
        var hasError = false;
        if ($radios.length > 0) {
            if (this.$el.find('input[type="radio"]:checked').length === 0) {
                hasError = true;
            }
        }
        if ($inputs.length > 0) {
            $.each($inputs, function(k,v){
                $(v).parent().removeClass('has-error');
                if (v.value === undefined || v.value === ''){
                    hasError = true;
                    $(v).parent().addClass('has-error');
                }
            });
        }
        if ($selects.length > 0) {
            $.each($inputs, function(k,v){
                $(v).parent().removeClass('has-error');
                if (v.value === undefined || v.value === ''){
                    hasError = true;
                    $(v).parent().addClass('has-error');
                }
            });
        }
        if (hasError) {
            this.show_error("Error: please fill all the fields");
        }
        return hasError;
    },

    process_next_step: function() {
        //Call function to check empty field
        if (this.check_empty_field()) {
            return false;
        }
        return true;
        //To be implemented by children widget
    },

    process_mfa_step: function() {
        if (this.check_empty_field()) {
            return false;
        }
        return true;
        //To be implemented by children widget
    },

    complete_process: function(){
        if (this.check_empty_field()) {
            return false;
        }
        return true;
        //To be implemented by children widget
    },

    show_error: function(message, errorCode) {
        framework.unblockUI();
        this.$el.find('.js_online_sync_wait').hide();
        if (message === false) {
            message = "An error occured!";
        }
        if (errorCode != undefined) {
            message = message + " (error Code: "+errorCode+")";
        }
        $(this.$el).find('.error_msg').text(message)
        $(this.$el).find('.error').removeClass('hide');
    },

    hide_error: function() {
        this.$el.find('.error').addClass('hide');
    },

    launch_configurator_wizard: function(result) {
        var self = this;
        //Process json_result and open dialog
        this.post_process_connection_result(result);
        this.replaceElement($(QWeb.render(self.config_template, self.config_template_data)));
        this.bind_button();
    },

    fetch_site_info: function() {
        //Call to server must be implemented by children widget
    },


    init: function(parent, context) {
        // Note: context should always be present in the action and it should always contain
        // the following keys: 'journal_id' and 'online_id' for this widget to work correctly
        this._super(parent, context);
        if (context.context !== undefined) {
            this.id = context.context.journal_id;
            this.online_id = context.context.online_id;
            this.online_institution_id = context.context.online_institution_id;
        }
        this.is_modal = true;
        if (context.target !== 'new'){
            this.is_modal = false;
        }
    },


    renderElement: function() {
        var self = this;
        var fetch_site_info = this.fetch_site_info()
                        .then(function(result){
                            self.launch_configurator_wizard(JSON.parse(result));
                        });
    },

    attach_datepicker: function() {
        var current_date = new moment();
        var dp = new datepicker.DateWidget(this);
        dp.appendTo(this.$el.find('.js_online_sync_date'));
        dp.set_value(current_date.subtract(15, 'days'));
        this.datepicker = dp;
    },
});

//Old plaid-yodlee compatibility widget for v9 -> to be remove in v10
var OnlineSynchAccountConfigurationWidgetOld = form_relational.FieldMany2One.extend({

    is_false: function() {
        return false;
    },
    render_value: function() {
        var self = this;
        var res = this._super();
        if (this.$el.find('.js_configure_online_account').length === 0){
            this.$el.append('<a href="#" class="js_configure_online_account">(-> Configure)</a>');
            this.$('.js_configure_online_account').click(function(event){
                //When clicking widget, ensure that view is not in edit to prevent inconsistance with server value
                //Also preventdefault to prevent changing url with an incorrect hash
                event.preventDefault();
                event.stopPropagation();
                self.view.save().then(function(result){
                    self.view.to_view_mode();
                    
                    var journal_id = self.view.fields.journal_id.get("value");
                    return new Model('account.journal').call('launch_wizard', [[journal_id]]).then(function(result){
                        self.do_action(result);
                    });
                });
            });
        }
        return res;
    },

});

//Old widgets compatibility for v9 
core.form_widget_registry.add('yodleeAccountConfiguration', OnlineSynchAccountConfigurationWidgetOld);
core.form_widget_registry.add('plaidAccountConfiguration', OnlineSynchAccountConfigurationWidgetOld);

return {
    OnlineSynchAccountConfigurationWidget: OnlineSynchAccountConfigurationWidget,
}

});
