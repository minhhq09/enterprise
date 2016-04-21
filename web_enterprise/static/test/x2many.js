// Modifies selectors of steps accessing the menu as it differs from community
odoo.define('web_enterprise.test.x2many', function (require) {
'use strict';

var Tour = require('web.Tour');
require('web.test.x2many');

var steps = Tour.tours.widget_x2many.steps;
_.findWhere(steps, {
    title: 'switch to the second form view to test one2many with editable list (toggle menu dropdown)'
}).element = 'nav .o_menu_sections li a:containsExact(Discussions)';
_.findWhere(steps, {
    title: 'switch to the second form view to test one2many with editable list (open submenu)'
}).element = 'nav .o_menu_sections ul li a:contains(Discussions 2)';

});
