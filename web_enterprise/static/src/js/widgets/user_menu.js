odoo.define('web_enterprise.UserMenu', function (require) {
"use strict";

var UserMenu = require('web.UserMenu');

UserMenu.include({
    on_menu_support: function () {
        window.location.href = 'mailto:help@odoo.com';
    },
});

});
