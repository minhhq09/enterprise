odoo.define('web.test.menu', function (require) {
"use strict";

var Tour = require('web.Tour');

Tour.register({
    id:   'test_menu',
    name: "Test all menu items",
    path: '/web',
    mode: 'test',
    steps: [
        {
            title:     "begin test",
        },

        // log as admin
        {
            title:     "log on as admin",
            element:   ".oe_login_form button",
            onload: function () {
                $('input[name="login"], input[name="password"]').val("admin");
                localStorage.setItem('user', 'admin');
            },
        },
        {
            title:     "click on Settings",
            waitFor:   '.o_application_switcher',
            waitNot:   '.o_loading:visible',
            element:   '.o_application_switcher a[data-menu]:contains(Settings)',
        },

        //  add technical features to admin user
        {
            title:     "click on Admin",
            element:   '.o_list_view td:contains(Admin)',
        },
        {
            waitFor:   '.breadcrumb li:contains(Admin)',
            waitNot:   ".o_loading:visible",
        },
        {
            title:     "click on Edit button",
            element:   'button.o_form_button_edit',
        },
        {
            title:     "click on Technical Features",
            element:   'td:contains(Technical Features) + td input:not(:disabled):visible',
            onend: function () {
                $('td:contains(Technical Features) + td input:not(:disabled):visible').attr("checked", true);
            },
        },
        {
            title:     "click on Save User",
            element:   'button.o_form_button_save',
        },

        //  add technical features to demo user
        {
            title:     "click on Users",
            element:   '.breadcrumb .o_back_button',
            waitFor:   'td:contains(Technical Features) + td input:disabled:visible',
        },
        {
            title:     "click on Demo User",
            element:   '.o_list_view td:contains(Demo)',
        },
        {
            waitFor:   '.breadcrumb li:contains(Demo)',
            waitNot:   ".o_loading:visible",
        },
        {
            title:     "click on Edit button",
            element:   'button.o_form_button_edit',
        },
        {
            title:     "click on Technical Features",
            element:   'td:contains(Technical Features) + td input:not(:disabled):visible',
            onend: function () {
                $('td:contains(Technical Features) + td input:not(:disabled):visible').attr("checked", true);
            },
        },
        {
            title:     "click on Save User",
            waitFor:   'td:contains(Technical Features) + td input:checked:not(:disabled):visible',
            element:   'button.o_form_button_save',
        },
        {
            title:     "toggle app switcher",
            waitFor:   'td:contains(Technical Features) + td input:disabled:visible',
            element:   '.o_menu_toggle',
        },
        {
            title:     "wait for app switcher",
            waitFor:   ".o_application_switcher",
        },

        // click all menu items
        {
            title:     "click on top menu",
            element:   '.o_application_switcher a[data-menu]:not([data-action-model="ir.actions.act_url"]):not(.already_tested):first',
            next:      "check",
            onload: function () {
                this.$current_app = $(this.element);
                console.log("Tour 'test_menu' click on App: '" +
                    this.$current_app.text().replace(/^\s+|\s+$/g, '') + "'");
            },
            onend: function () {
                this.$current_app.addClass('already_tested');
            },
        },
        {
            title:     "click on sub menu",
            waitFor:   '.o_content',
            waitNot:   '.o_loading:visible',
            element:   '.o_menu_sections a:not(.dropdown-toggle):visible:not(.already_tested):first',
            next:      "check",
            onload: function () {
                $('.o_menu_sections .dropdown-menu').show();
                console.log("Tour 'test_menu' click on Menu: '" +
                    $(this.element).find('span:first').text().replace(/^\s+|\s+$/g, '') + "'");
            },
            onend: function () {
                $(this.element).addClass('already_tested');
            },
        },
        {
            title:     "click on switch view",
            waitNot:   '.o_loading:visible',
            element:   '.o_cp_switch_buttons button:not(.already_tested):first',
            next:      "check",
            onload: function () {
                console.log("Tour 'test_menu' click on switch view: '" +
                    $(this.element).data('original-title') + "'");
            },
            onend: function () {
                $(this.element).addClass('already_tested');
            },
        },
        {
            title:     "back to app switcher",
            element:   '.o_menu_toggle',
            next:      "check",
        },
        {
            title:    "check",
            waitNot:  ".o_loading:visible",
            onerror: function () {
                return "Select next action";
            }
        },
        {
            title:    "Select next action",
            onload: function () {
                if ($(".o_error_detail").size()) {
                    console.log("Error: Tour 'test_menu' has detected an error.");
                }
                if ($(".o_dialog_warning").size()) {
                    console.log("Warning: Tour 'test_menu' has detected a warning.");
                }

                $('.modal').modal('hide').remove();

                var steps = ["click on switch view", "click on sub menu", "click on top menu", "back to app switcher"];
                for (var k in steps) {
                    var step = Tour.search_step(steps[k]);
                    if ($(step.element).size()) {
                        return step.id;
                    }
                }

                // end tour if we had tested admin and demo user
                if (localStorage.getItem('user') === "demo") {
                    return "finish";
                }
            },
        },

        // log out and re-run as demo user
        {
            title:     "open user menu",
            wait:      50,
            onload: function() {
                $('.o_user_menu ul').show();
            },
        },
        {
            title:     "logout admin",
            element:   'a[data-menu="logout"]',
        },
        {
            title:     "log on as demo user",
            wait:      '.oe_login_form',
            element:   '.oe_login_form button',
            onload: function () {
                $('input[name="login"], input[name="password"]').val("demo");
                localStorage.setItem('user', 'demo');
            },
        },
        {
            title:     "wait for app switcher and re-run as demo user",
            waitFor:   ".o_application_switcher",
            next:      "check",
        },

        // finish tour
        {
            title:     "finish",
        }
    ]
});

});
