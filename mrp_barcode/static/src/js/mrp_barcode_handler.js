odoo.define('mrp_barcode.MrpBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Dialog = require('web.Dialog');
var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');

var _t = core._t;


var WorkorderBarcodeHandler = FormViewBarcodeHandler.extend({
    start: function() {
        var def = this._super.apply(this, arguments);
        this.form_view.options.disable_autofocus = 'true';
        return def;
    },
});


core.form_widget_registry.add('workorder_barcode_handler', WorkorderBarcodeHandler);

});

