odoo.define('web_studio.SearchEditor', function (require) {
"use strict";

var Widget = require('web.Widget');

return Widget.extend({
    start: function() {
        this.$el.empty();
        var $search_view = $('<div>').addClass('o_web_studio_no_preview').html('Preview not available yet.');
        this.$el.html($search_view);
        return this._super.apply(this, arguments);
    },
});

});
