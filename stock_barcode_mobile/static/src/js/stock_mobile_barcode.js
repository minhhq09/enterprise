odoo.define('web.stock.mobile_barcode', function (require) {
"use strict";

var BarcodeMainMenu = require('stock_barcode.MainMenu').MainMenu;
var mobile_utility = require('mobile.utility');

BarcodeMainMenu.include({
    events: _.defaults({
        'click .o_stock_mobile_barcode': 'open_mobile_scanner'
    }, BarcodeMainMenu.prototype.events),
    start: function(){
        if(!mobile_utility.Available){
            this.$el.find(".o_stock_mobile_barcode").remove();
        }
        return this._super.apply(this, arguments);
        
    },
    open_mobile_scanner: function(){
        var self = this;
        mobile_utility.barcode.scanBarcode({}).then(function(response){
            var barcode = response.data;
            if(barcode){
                self.on_barcode_scanned(barcode);
                mobile_utility.notify.vibrate({'duration': 100});
            }else{
                mobile_utility.notify.showToast({'message':'Please, Scan again !!'});
            }
        });
    }
});


});
