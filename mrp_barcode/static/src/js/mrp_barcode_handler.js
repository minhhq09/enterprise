odoo.define('mrp_barcode.MrpBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Dialog = require('web.Dialog');
var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');

var _t = core._t;

var ProductionBarcodeHandler = FormViewBarcodeHandler.extend({
    init: function(parent, context) {
        if (parent.ViewManager.action) {
            this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode;
        } else if (parent.ViewManager.view_form) {
            this.form_view_initial_mode = parent.ViewManager.view_form.options.initial_mode;
        }
        //this.m2x_field = 'move_raw_ids';
        //this.quantity_field = 'quantity_done';
        
        return this._super.apply(this, arguments);
    },
    start: function() {
        this._super();
        this.StockMove = new Model("stock.move");
        this.MrpProduction = new Model("mrp.production");
        this.map_barcode_method['O-CMD.MAIN-MENU'] = _.bind(this.do_action, this, 'stock_barcode.stock_barcode_action_main_menu', {clear_breadcrumbs: true});
        // FIXME: start is not a reliable place to do this.
        this.form_view.options.disable_autofocus = 'true';
        if (this.form_view_initial_mode) {
            this.form_view.options.initial_mode = this.form_view_initial_mode;
        }
    },
    pre_onchange_hook: function(barcode) {
        var self = this;
        var state = this.form_view.datarecord.state;
        var deferred = $.Deferred();
        if (state === 'cancel' || state === 'done') {
            this.do_warn(_.str.sprintf(_t('Manufacturing %s'), state), _.str.sprintf(_t('The manufacturing order is %s and cannot be edited.'), state));
            return deferred.reject();
        }
        return self.update_raw_material_qty(barcode).fail(function() {
            return self.open_lot_splitting_wizard(barcode).fail(function() {
                return Dialog.alert(self, _.str.sprintf(_t("Can not find consumed material for this corresponding barcode %s."), barcode), {
                    title: _t('Warning'),
                });
            }).done(function() { deferred.resolve(); });
        }).done(function() { deferred.resolve(); });
    },
    _get_candidates: function(mo_records, is_suitable) {
        if (mo_records.records) {
            return mo_records.find(function(mo) { return is_suitable(mo); });
        } else {
            return _.find(mo_records, function(mo) { return is_suitable(mo); });
        }
    },
    update_raw_material_qty: function(barcode) {
        function is_suitable(stock_move) {
            return stock_move.get('product_barcode') == barcode && stock_move.get('has_tracking') == 'none' && !stock_move.get('is_done')
        }
        var mo_field = this.form_view.fields.move_raw_ids;
        var mo_records = this._get_records(mo_field);
        var candidate = this._get_candidates(mo_records, is_suitable);
        if (candidate) {
            return mo_field.data_update(candidate.get('id'), {'quantity_done': candidate.get('quantity_done') + 1}).then(function() {
                return mo_field.viewmanager.active_view.controller.reload_record(candidate);
            });
        } else {
            return $.Deferred().reject();
        }
    },
    open_lot_splitting_wizard: function(barcode) {
        function is_suitable(stock_move) {
            return stock_move.get('product_barcode') == barcode && stock_move.get('has_tracking') != 'none' && !stock_move.get('is_done')
        }
        var mo_field = this.form_view.fields.move_raw_ids;
        var mo_records = this._get_records(mo_field);
        var candidate = this._get_candidates(mo_records, is_suitable);
        if (candidate) {
            var self = this;
            return self.MrpProduction.call('move_for_barcode', [[self.form_view.datarecord.id], barcode]).done(function(id) {
                return self.StockMove.call("split_move_lot", [[id]]).done(function(result) {
                    self.do_action(result, {
                        on_close: function() {
                            self.form_view.trigger('attached');
                            self.form_view.reload();
                        }
                    });
                });
            });
        } else {
            return $.Deferred().reject();
        }
    },
});

var WorkorderBarcodeHandler = FormViewBarcodeHandler.extend({
    init: function(parent, context) {
        return this._super.apply(this, arguments);
    },
    start: function() {
        this._super();
        this.MrpWorkorder = new Model("mrp.workorder");
    },
    _get_move_lot: function(lot_records, is_suitable) {
        if (lot_records.records) {
            return lot_records.find(function(wo) { return is_suitable(wo) });
        } else {
            return _.find(lot_records, function(wo) { return is_suitable(wo) });
        }
    },
    pre_onchange_hook: function(barcode) {
        var self = this;
        var deferred = $.Deferred();
        function is_suitable(stock_move_lot) {
            return stock_move_lot.get('lot_barcode') == barcode || stock_move_lot.get('lot_id') == false
        }
        return this.MrpWorkorder.call('move_lot_update_qty', [[self.form_view.datarecord.id], barcode]).done(function(result) {
            return self.form_view.save().done(function() {
                if (result && result.warning) {
                    return Dialog.alert(self, _.str.sprintf(_t(result.warning)), {
                        title: _t('Warning'),
                    });
                }
                var active_lot = self.form_view.fields.active_move_lot_ids;
                var lot_records = self._get_records(active_lot);
                var candidate = self._get_move_lot(lot_records, is_suitable);
                if (candidate && result) {
                    return active_lot.viewmanager.active_view.controller.reload_record(candidate);
                }
                return self.form_view.reload().then(function(){
                    $(self.form_view.fields.qty_producing.$el[0]).blur()
                });
            });
        });
        return deferred;
    },
});


core.form_widget_registry.add('production_barcode_handler', ProductionBarcodeHandler)
                         .add('workorder_barcode_handler', WorkorderBarcodeHandler);

});
