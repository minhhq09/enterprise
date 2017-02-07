odoo.define("website_helpdesk.menu", function (require) {
    "use strict";

    require("web_editor.base");

    var pathname = $(location).attr("pathname");
    var $link = $(".team_menu li a");
    if (pathname !== "/helpdesk/") {
        $link = $link.filter("[href$='" + pathname + "']");
    }
    $link.first().closest("li").addClass("active");

    // 'Show more' / 'Show less' buttons
    $('.o_my_show_more').click(function(e) {
        e.preventDefault();
        $(e.target).addClass('hidden');
        $('.o_my_show_less').removeClass('hidden');
        $('.to_hide').removeClass('hidden');
    });
    $('.o_my_show_less').click(function(e) {
        e.preventDefault();
        $(e.target).addClass('hidden');
        $('.o_my_show_more').removeClass('hidden');
        $('.to_hide').addClass('hidden');
    });

});
