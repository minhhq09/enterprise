odoo.define('web_studio.PivotEditor', function (require) {
"use strict";

var OldViewRenderers = require('web_studio.OldViewRenderers');

return OldViewRenderers.extend({
    view_type: 'pivot',
});

});
