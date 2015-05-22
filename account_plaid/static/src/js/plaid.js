odoo.define('plaid_form_widgets', function(require) {
"use strict";

var core = require('web.core')
var common = require('web.form_common');
var QWeb = core.qweb;
var _t = core._t;
/**
 * Create new plaid widget.
 * Used to show selections question
 */
var ShowSelectionsLineWidget = common.AbstractField.extend({
    events: {
	'change .choices': 'compute_response',
    },
    render_value: function(){
	var self = this;
	if (this.field_manager.datarecord.selections){
	    var json = JSON.parse(this.field_manager.datarecord.selections)
	    this.$el.append(QWeb.render('SelectionsTemplate', {mfa: json.mfa}))
	    this.compute_response();
	}
    },
    compute_response: function(){
	var resp = _.map(this.$el.find(".choices"), function(choice){ return choice.value; });
	var resp_str = "[\"" + resp.join("\", \"") + "\"]";
	this.field_manager.set_values({'response': resp_str});
    },
});

/**
 * Registry of form fields
 */
core.form_widget_registry
    .add('plaid_selections', ShowSelectionsLineWidget);
});
