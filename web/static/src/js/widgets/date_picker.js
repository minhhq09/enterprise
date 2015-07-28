odoo.define('web.datepicker', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var time = require('web.time');
var Widget = require('web.Widget');

var _t = core._t;

var DateWidget = Widget.extend({
    template: "web.datepicker",
    type_of_date: "date",
    events: {
        'dp.change': 'change_datetime',
        'dp.show': 'set_datetime_default',
        'keypress .o_datepicker_input': 'change_datetime',
    },
    init: function(parent) {
        this._super(parent);
        this.name = parent.name;
    },
    start: function() {
        var l10n = _t.database.parameters;
        var options = {
            pickTime: true,
            useSeconds: true,
            startDate: moment({ y: 1900 }),
            endDate: moment().add(200, "y"),
            calendarWeeks: true,
            icons : {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down'
               },
            language : moment.locale(),
            format : time.strftime_to_moment_format(l10n.date_format +' '+ l10n.time_format),
        };
        this.$input = this.$('input.o_datepicker_input');
        if (this.type_of_date === 'date') {
            options.pickTime = false;
            options.useSeconds = false;
            options.format = time.strftime_to_moment_format(l10n.date_format);
        }
        this.$el.datetimepicker(options);
        this.picker = this.$el.data('DateTimePicker');
        this.set_readonly(false);
        this.set({'value': false});
    },
    set_value: function(value_) {
        this.set({'value': value_});
        this.$input.val(value_ ? this.format_client(value_) : '');
        this.picker.setValue(value_);
    },
    get_value: function() {
        return this.get('value');
    },
    set_value_from_ui_: function() {
        var value_ = this.$input.val() || false;
        this.set_value(this.parse_client(value_));
    },
    set_readonly: function(readonly) {
        this.readonly = readonly;
        this.$input.prop('readonly', this.readonly);
    },
    is_valid_: function() {
        var value_ = this.$input.val();
        if (value_ === "") {
            return true;
        } else {
            try {
                this.parse_client(value_);
                return true;
            } catch(e) {
                return false;
            }
        }
    },
    parse_client: function(v) {
        return formats.parse_value(v, {"widget": this.type_of_date});
    },
    format_client: function(v) {
        return formats.format_value(v, {"widget": this.type_of_date});
    },
    set_datetime_default: function(){
        //when opening datetimepicker the date and time by default should be the one from
        //the input field if any or the current day otherwise
        if (this.type_of_date === 'datetime') {
            var value = moment().second(0);
            if (this.$input.val().length !== 0 && this.is_valid_()){
                value = this.$input.val();
            }
            this.$el.data('DateTimePicker').setValue(value);
        }
    },
    change_datetime: function(e) {
        if ((e.type !== "keypress" || e.which === 13) && this.is_valid_()) {
            this.set_value_from_ui_();
            this.trigger("datetime_changed");
        }
    },
    commit_value: function () {
        this.change_datetime();
    },
    destroy: function () {
        this.picker.destroy();
        this._super();
    },
});

var DateTimeWidget = DateWidget.extend({
    type_of_date: "datetime"
});

return {
    DateWidget: DateWidget,
    DateTimeWidget: DateTimeWidget,
};

});
