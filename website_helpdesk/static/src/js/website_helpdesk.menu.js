odoo.define("website_helpdesk.menu", function (require) {
    "use strict";

    require("web_editor.base");

    var pathname = $(location).attr("pathname");
    var $link = $(".team_menu li a");
    if (pathname !== "/helpdesk/") {
        $link = $link.filter("[href$='" + pathname + "']");
    }
    $link.first().closest("li").addClass("active");
});
