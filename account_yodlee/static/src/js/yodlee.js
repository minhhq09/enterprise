odoo.define('account_yodlee.acc_config_widget', function(require) {
"use strict";

var core = require('web.core');
var common = require('web.form_common');
var Model = require('web.Model');
var framework = require('web.framework');
var online_sync = require('account_online_sync.acc_config_widget');

var QWeb = core.qweb;
var _t = core._t;


var YodleeAccountConfigurationWidget = online_sync.OnlineSynchAccountConfigurationWidget.extend({

    map_field_type: function(fieldType){
        switch (fieldType){
            case 'TEXT':
                return 'text';
            case 'IF_PASSWORD':
                return 'password';
            case 'OPTIONS':
                return 'option';
            case 'CHECKBOX':
                return 'checkbox';
            case 'RADIO':
                return 'radio';
            // case 'IF_LOGIN':
            // case 'URL':
            // case 'HIDDEN':
            // case 'IMAGE_URL':
            // case 'CONTENT_URL':
            // case 'CUSTOM':
            // case 'CLUDGE':
            //     return 'text';
            case 'SECURITY_QUESTION':
                return 'security';
            case 'TOKEN_ID':
                return 'token';
            case 'IMAGE':
                return 'image';
            default:
                return 'text';
        }
    },

    post_process_connection_result: function(resp_json) {
        var self = this;
        this._super();

        //process login form
        var inputs_vals = []
        this.response = {'siteId': this.view.fields.online_id.get("value"),
                         'credentialFields.enclosedType': 'com.yodlee.common.FieldInfoSingle'}
        $.each(resp_json.componentList, function(k,v) {
            if (v.isOptional == false || v.isOptional == undefined) {
                var vals = {displayName: v.displayName,
                    fieldType: self.map_field_type(v.fieldType.typeName),
                    indexResponse: k,
                    maxlength: v.maxlength || -1,
                    selectValues: v.validValues,}
                inputs_vals = inputs_vals.concat(vals);
                //Prepare response dict
                self.response['credentialFields['+k+'].displayName'] = v.displayName;
                self.response['credentialFields['+k+'].fieldType.typeName'] = v.fieldType.typeName;
                self.response['credentialFields['+k+'].name'] = v.name;
                self.response['credentialFields['+k+'].size'] = v.size;
                self.response['credentialFields['+k+'].valueIdentifier'] = v.valueIdentifier;
                self.response['credentialFields['+k+'].valueMask'] = v.valueMask;
                self.response['credentialFields['+k+'].isEditable'] = v.isEditable;
            }
        });
        this.config_template_data = {inputs: inputs_vals};
    },

    process_next_step: function() {
        var self = this;
        if (this._super()){
            var inputs = $(".js_online_sync_input");
            _.each(inputs, function(input){
                self.response['credentialFields[' + input.id + '].value'] = input.value;
            });
            framework.blockUI();
            var request = new Model('account.journal').call('fetch', [[this.id], '/jsonsdk/SiteAccountManagement/addSiteAccount1', this.online_type, this.response])
                .then(function(result){
                    var resp_json = JSON.parse(result);
                    //Check for error and exception first
                    if (resp_json.siteRefreshInfo === undefined || resp_json.errorOccurred === "true"){
                        self.show_error("ERROR: " + resp_json.exceptionType);
                    }
                    //Check siteRefreshStatus, should be REFRESH_TRIGGERED
                    if (resp_json.siteRefreshInfo.siteRefreshStatus.siteRefreshStatus === 'REFRESH_TRIGGERED'){
                        //Check if MFA needed
                        self.siteAccountId = resp_json.siteAccountId;
                        if (resp_json.siteRefreshInfo.siteRefreshMode.refreshMode === 'MFA'){
                            self.get_mfa_process(resp_json.siteAccountId);
                        }
                        else {
                            self.refresh_process(resp_json.siteAccountId, 30);
                        }
                    }
                    else{
                        self.show_error("Incorrect Refresh state received", resp_json.siteRefreshInfo.siteRefreshStatus.siteRefreshStatus);
                    }

                });
        }
    },

    complete_process: function() {
        var self = this;
        if (this._super()){
            //Get back sync date information and selected account_id and create online.account object with those information
            var sync_date = this.datepicker.get_value();
            var option_selected = this.configurator_wizard.$el.find('input[name="account-selection"]:checked');
            var account_name = option_selected.attr('value');
            var account_id = option_selected.attr('account');
            var rpc = new Model('account.journal').call('save_online_account', [[this.id], {'last_sync': sync_date, 'site_account_id': this.siteAccountId, 'account_id': account_id, 'name': account_name, 'journal_id': this.id}, this.online_institution_id])
                .then(function(result) {
                    self.configurator_wizard.close();
                    self.do_action(result);
                });
        }
    },

    show_account_selector: function(resp_json) {
        framework.unblockUI();
        var self = this;
        var data = [];
        var selected = true;
        $.each(resp_json, function(k,v){
            // if (v.contentServiceInfo.containerInfo.containerName === 'credits' || v.contentServiceInfo.containerInfo.containerName === 'bank') {
                $.each(v.itemData.accounts, function(index, value){
                    data = data.concat({
                        name: value.accountName,
                        accountId: value.itemAccountId,
                        containerType: v.contentServiceInfo.containerInfo.containerName,
                        checked: selected,
                    });
                    selected = false;
                });
            // }
        });
        this.configurator_wizard.$footer.find('.js_process_next_step').hide();
        this.configurator_wizard.$footer.find('.js_process_mfa_step').hide();
        this.configurator_wizard.$footer.find('.js_conclude_configuration').toggleClass('hide');
        this.configurator_wizard.$el.find('.js_online_sync_form').html(QWeb.render('OnlineSynchAccountSelector', {accounts: data}));
        this.attach_datepicker();
    },

    refresh_process: function(siteAccountId, number) {
        //Call getSiteRefreshInfo
        var self = this;
        var params = {memSiteAccId: siteAccountId};
        if (number === 0) {
            // framework.unblockUI();
            self.show_error("Request Time Out");
        }
        else {
            var request = new Model('account.journal').call('fetch', [[this.id], '/jsonsdk/Refresh/getSiteRefreshInfo', this.online_type, params])
                .then(function(result){
                    var resp_json = JSON.parse(result);
                    var refresh_status = resp_json.siteRefreshStatus.siteRefreshStatus;
                    if (resp_json.code === undefined || resp_json.errorOccurred === "true"){
                        self.show_error("ERROR: " + resp_json.exceptionType);
                    }
                    if (resp_json.code === 801 || (resp_json.code === 0 && refresh_status !== 'REFRESH_COMPLETED' && refresh_status !== 'REFRESH_COMPLETED_ACCOUNTS_ALREADY_AGGREGATED')) {
                        if (refresh_status === 'REFRESH_TIMED_OUT'){
                            number = 1;
                        }
                        setTimeout(function(){self.refresh_process(siteAccountId, number-1)}, 2000);
                    }
                    else{
                        if (resp_json.code === 0) {
                            var get_account_request = new Model('account.journal').call('fetch', [[self.id], '/jsonsdk/DataService/getItemSummariesForSite', self.online_type, params])
                                .then(function(result){
                                    //Show selection of account and online sync date for user to choose
                                    self.show_account_selector(JSON.parse(result));
                                });
                        }
                        else {
                            //ERROR
                            // framework.unblockUI();
                            self.show_error(false, resp_json.code);
                        }   
                    }
            })
        }
    },

    get_mfa_process: function(siteAccountId) {
        var self = this;
        //Call getMFAResponseForSite to check if we have some MFA to complete
        var request = new Model('account.journal').call('fetch', [[this.id], '/jsonsdk/Refresh/getMFAResponseForSite', this.online_type, {memSiteAccId: siteAccountId}])
            .then(function(result){
                var resp_json = JSON.parse(result);
                if (resp_json.errorOccurred === 'true') {
                    self.show_error("ERROR: "+resp_json.detailedMessage);
                }
                if (resp_json.errorCode === undefined) {
                    if (resp_json.isMessageAvailable === true) {
                        //Present MFA to user
                        
                        self.show_mfa_to_user(resp_json, siteAccountId);
                    }
                    else {
                        self.get_mfa_process(siteAccountId);
                    }
                }
                else {
                    // framework.unblockUI();
                    if (resp_json.errorCode === 0) {
                        // framework.blockUI();
                        self.refresh_process(siteAccountId, 30);
                    }
                    else {
                        //ERROR
                        self.show_error(false, resp_json.errorCode);
                    }
                }
            });
    },

    show_mfa_to_user: function(resp_json, siteAccountId) {
        framework.unblockUI();
        var self = this;
        var v = resp_json.fieldInfo;
        // $.each(resp_json.fieldInfo, function(k, v){

        var qaquestions = [];
        self.qaResponse = {'memSiteAccId': siteAccountId};
        if (v.questionAndAnswerValues !== undefined){
            $.each(v.questionAndAnswerValues, function(k,value){
                if (value.isRequired === "true") {
                    qaquestions = qaquestions.concat({name: value.question, indexResponse: k});
                    self.qaResponse["userResponse.quesAnsDetailArray["+k+"].answerFieldType"] = value.responseFieldType;
                    self.qaResponse["userResponse.quesAnsDetailArray["+k+"].metaData"] = value.metaData;
                    self.qaResponse["userResponse.quesAnsDetailArray["+k+"].question"] = value.question;
                    self.qaResponse["userResponse.quesAnsDetailArray["+k+"].questionFieldType"] = value.questionFieldType;
                }
            });
        }

        var qdict = {name: v.displayString,
            fieldType: this.map_field_type(v.mfaFieldInfoType),
            image: v.image && btoa(String.fromCharCode.apply(null, new Uint8Array(v.image))),
            maxlength: v.maximumLength,
            questions: qaquestions,
        };
        // });
        this.configurator_wizard.$footer.find('.js_process_next_step').hide();
        this.configurator_wizard.$footer.find('.js_process_mfa_step').removeClass('hide');
        this.configurator_wizard.$el.find('.js_online_sync_form').html(QWeb.render('YodleeMFAResponse', {question: qdict}));
    },

    process_mfa_step: function() {
        var self = this;
        if (this._super()){
            if ($('.js_yodlee_captcha').length > 0){
                self.qaResponse['userResponse.objectInstanceType'] = 'com.yodlee.core.mfarefresh.MFAImageResponse';
                self.qaResponse['userResponse.imageString'] = $('.js_yodlee_captcha').val();
            }
            if ($('.js_yodlee_security').length > 0){
                self.qaResponse['userResponse.objectInstanceType'] = 'com.yodlee.core.mfarefresh.MFAQuesAnsResponse';
                $.each($('.js_yodlee_security'), function(k, value){
                    self.qaResponse['userResponse.quesAnsDetailArray['+value.id+'].answer'] = value.value;
                })
            }
            if ($('.js_yodlee_token').length > 0){
                self.qaResponse['userResponse.objectInstanceType'] = 'com.yodlee.core.mfarefresh.MFATokenResponse';
                self.qaResponse['userResponse.token'] = $('.js_yodlee_token').val();
            }
            var sent_request = new Model('account.journal').call('fetch', [[this.id], '/jsonsdk/Refresh/putMFARequestForSite', this.online_type, self.qaResponse])
                .then(function(result){
                    var resp_json = JSON.parse(result);
                    if (resp_json.primitiveObj === true) {
                        framework.blockUI();
                        self.get_mfa_process(self.siteAccountId);
                    }
                    else {
                        if (resp_json.errorOccurred === "true"){
                            self.show_error("ERROR: "+resp_json.detailedMessage);
                        }
                        else {
                            self.show_error("Error Occured, please close wizard and retry");
                        }
                    }
                });
        }
    },

    fetch_site_info: function() {
        this._super();
        this.online_type = 'yodlee';
        var param = {'siteId': this.online_id};
        return new Model('account.journal').call('fetch', [[this.id], '/jsonsdk/SiteAccountManagement/getSiteLoginForm', this.online_type, param]);
    },

});

core.form_widget_registry.add('yodleeAccountConfiguration', YodleeAccountConfigurationWidget);
    
});
