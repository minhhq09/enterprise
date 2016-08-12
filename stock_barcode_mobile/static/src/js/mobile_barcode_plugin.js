odoo.define('mobile.plugin.barcode', function (require) {
"use strict";

var MobilePlugin = require('mobile.plugin');


MobilePlugin.extend({
    plugin: "barcode",
    scanBarcode: function(data){
        return this.invoke("scanBarcode", data, true);
    }
});


});
