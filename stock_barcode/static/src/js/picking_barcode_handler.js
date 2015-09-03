odoo.define('stock_barcode.PickingBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');

var PickingBarcodeHandler = FormViewBarcodeHandler.extend({
    start: function() {
        this._super();
        this.po_model = new Model("stock.pack.operation");
        this.picking_model = new Model("stock.picking");
        this.map_barcode_method['O-CMD.MAIN-MENU'] = _.bind(this.do_action, this, 'stock_barcode.stock_barcode_action_main_menu', {clear_breadcrumbs: true});
        // FIXME: start is not a reliable place to do this.
        this.form_view.options.initial_mode = 'edit';
        this.form_view.options.disable_autofocus = 'true';
    },

    pre_onchange_hook: function(barcode) {
        var po_field = this.form_view.fields.pack_operation_product_ids;
        var po_view = po_field.viewmanager.active_view;

        if (! po_view) { // Weird, sometimes is undefined. Due to an asynchronous field re-rendering ?
            return false;
        }
        var split_lot_candidate = po_view.controller.records.find(function(record) {
            return record.get('product_barcode') === barcode && record.get('lots_visible') && ! record.get('location_processed') && ! record.get('result_package_id') && record.get('qty_done') < record.get('product_qty');
        });
        if (! split_lot_candidate)  {
            split_lot_candidate = po_view.controller.records.find(function(record) {
                return record.get('product_barcode') === barcode && record.get('lots_visible') && ! record.get('location_processed') && ! record.get('result_package_id');
            });
        }
        var inc_qty_candidate = po_view.controller.records.find(function(record) {
            return record.get('product_barcode') === barcode && ! record.get('lots_visible') && ! record.get('location_processed') && ! record.get('result_package_id') && record.get('qty_done') < record.get('product_qty');
        });
        if (! inc_qty_candidate)  {
            inc_qty_candidate = po_view.controller.records.find(function(record) {
                return record.get('product_barcode') === barcode && ! record.get('lots_visible') && ! record.get('location_processed') && ! record.get('result_package_id');
            });
        }

        if (split_lot_candidate) {
            var self = this;
            var deferred = $.Deferred();
            self.form_view.save().done(function() { self.form_view.reload().done(function() {
                self.picking_model.call('get_po_to_split_from_barcode', [[self.form_view.datarecord.id], barcode]).then(function(id) {
                    self.po_model.call("split_lot", [[id]]).then(function(result) {
                        self.open_wizard(result);
                        deferred.resolve();
                    });
                });});
            });
            return deferred;
        } else if (inc_qty_candidate) {
            return po_field.data_update(inc_qty_candidate.get('id'), {'qty_done': inc_qty_candidate.get('qty_done') + 1}).then(function() {
                return po_view.controller.reload_record(inc_qty_candidate);
            });
        } else {
            return false;
        }
    },

    open_wizard: function(action) {
        var self = this;
        this.form_view.trigger('detached');
        this.do_action(action, {
            on_close: function() {
                self.form_view.trigger('attached');
                self.form_view.reload();
            }
        });
    }
});

core.form_widget_registry.add('picking_barcode_handler', PickingBarcodeHandler);

});
