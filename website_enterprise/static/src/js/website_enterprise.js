odoo.define('website.app_switcher', function(require) {
    'use strict';

    var session = require('web.session');
    var website = require('website.website');

    website.TopBar.include({
        start: function() {
            this.$el.one('click', '.o_menu_toggle', function (e) {
                e.preventDefault();

                // We add a spinner for the user to understand the loading.
                $(e.currentTarget).find('span.fa').removeClass('fa-th').addClass('fa-spin fa-spinner');
                window.location.href = "/web" + ((session.debug)? '?debug' : '');
            });

            return this._super.apply(this, arguments);
        },
    });
});
