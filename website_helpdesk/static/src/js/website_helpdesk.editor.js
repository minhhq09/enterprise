odoo.define('website_helpdesk.editor', function (require) {
"use strict";

var core = require('web.core');
var contentMenu = require('website.contentMenu');
var website = require('website.website');

var _t = core._t;

var pathname = $(location).attr('pathname');
if (pathname == '/helpdesk/'){
    $(".team_menu li").first().addClass('active');
}
else {
    $(".team_menu li a[href$='" + pathname + "']:first").parents('li').addClass('active');
}

contentMenu.TopBar.include({
    new_team: function() {
        website.prompt({
            id: "editor_new_team",
            window_title: _t("New Team"),
            input: "Team Name",init: function () {
                var $group = this.$dialog.find("div.form-group");
                $group.removeClass("mb0");

                var $add = $(
                    '<div class="form-group mb0">'+
                        '<label class="col-sm-offset-3 col-sm-9 text-left">'+
                        '    <input type="checkbox" required="required"/> '+
                        '</label>'+
                    '</div>');
                $add.find('label').append(_t("Add page in menu"));
                $group.after($add);
            }
        }).then(function (team_name, field, $dialog) {
            var add_menu = ($dialog.find('input[type="checkbox"]').is(':checked'));
            website.form('/team/new', 'POST', {
                team_name: team_name,
                add_menu: add_menu || ""
            });
        });
    },
});

});
