/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2016  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

/*
 * Requires : jQuery
 *            creme
 */

creme.menu = {};
creme.menu.actions = {};

/* TODO : Seems never used. remove it ? */
/*
creme.menu.actions.flatMenu = function(trigger_selector, content_selector) {
    $(trigger_selector).menu({
            content: $(content_selector).html(),
            showSpeed: 400
    });

    // TODO : jquery 1.9x migration : live() is replaced by on(). menu is deprecated, so is it usefull ?
    $('[role=menuitem]','[aria-labelledby="' + trigger_selector.replace('#', '') + '"]')
    .live('menu-item-selected', function(e, menu) {
        e.stopImmediatePropagation();

        var $a = $('a:first', this);

        //TODO: use 3 classes: 'confirm', 'post', 'ajax'
        if($a.hasClass('confirm')) {
            creme.utils.confirmBeforeGo($a.attr('href'), true, {type: "POST"});
        } else {
            creme.utils.goTo($a.attr('href'));
        }
    });
};
*/

creme.menu.NavIt = function(trigger_selector, options, listeners) {
    var options = options || {};
    var listeners = listeners || {};

    $(trigger_selector).NavIt(options);
    $(trigger_selector).find('a').click(function(e) {
        e.preventDefault();

        var $a = $(this);
        var confirm   = $a.hasClass('confirm');
        var action    = $a.hasClass('post') ? 'post' : 'get';
        var ajax      = $a.hasClass('ajax');
        var url       = $a.prop('href');

        if (ajax)
        {
            var queryOptions = $.extend({action:action, link:$a}, options.queryOptions || {});

            if (confirm) {
                creme.utils.confirmAjaxQuery(url, queryOptions)
                           .on(listeners).start();
            } else {
                creme.utils.ajaxQuery(url, queryOptions)
                           .on(listeners).start();
            }
        }
        else
        {
            if (confirm) {
                creme.utils.confirmBeforeGo(url, ajax, opts);
            } else {
                creme.utils.goTo(url);
            }
        }
        /*
        var opts = {
            type: (post)? "POST": "GET"
        }

        e.preventDefault();

        if (ajax && list_view) {
            opts = $.extend(opts, {
                success: function(data, status, req) {
                    //creme.utils.showDialog(gettext("Operation done"));
                    $a.parents('form').list_view('reload');
                },
                error: function(req, status, error) { //TODO: factorise
//                     if(!req.responseText || req.responseText == "") {
//                         creme.utils.showDialog(gettext("Error"));
//                     } else {
//                         creme.utils.showDialog(req.responseText);
//                     }
                    creme.dialogs.warning(req.responseText || gettext("Error"));
                }
            });
        }

        if (confirm) {
            creme.utils.confirmBeforeGo($a.attr('href'), ajax, opts);
        } else {
            creme.utils.goTo($a.attr('href'));
        }*/

    });
};

creme.menu.HNavIt = function(trigger_selector, options, listeners) {
    creme.menu.NavIt(trigger_selector, $.extend({ArrowSideOnRight: false}, options || {}), listeners);
}

creme.menu.sideMenu = function(options) {
    var document_width_onload  = $(document).width();
    var document_height_onload = $(document).height();

    function activeEventsMenu() {
        // 'fast' transition makes bugs in chrome < 6.1
        $("#menu_collapse").mouseenter(function(e) {
            $("#menu_expanded").show('fast');
            $("#menu_collapse").hide('fast');
        });

        $("#menu_expanded").mouseleave(function(e) {
            $("#menu_expanded").hide('fast');
            $("#menu_collapse").show('fast');
        });
    }

    function desactiveEventsMenu() {
        $("#menu_collapse").unbind('mouseenter');
        $("#menu_expanded").unbind('mouseleave');
    }

    function resizePageElements(menu_width, expanded) {
        var top = $('#top');
        var content = $('#content');
        var footer = $('#footer');

        var margin_left = (expanded) ? menu_width + 5 + 'px' : menu_width;

        top.css('margin-left', margin_left);
        content.css('margin-left', margin_left);
        footer.css('margin-left', margin_left);

        var new_width = document_width_onload - menu_width;
        if(expanded) new_width -= 10;
        top.width(new_width);
        content.width(new_width);
        footer.width(new_width);
    }

    //var content_height = $("#content").height()+$("#footer").height()+$("#top").height();//$('#footer').offset().top;//
    var logo_container_height = $('#logo_container').outerHeight();
    //var max_menu_height = content_height - logo_container_height;

    var height = $('#menu_expanded').outerHeight();

    $('#menu').menu({
        content: $('#tree_menu2').html(),
        flyOut: false,
        backLink: false,
        alwaysOpen:true,
        maxHeight: height,
        crumbDefaultText : options.title,
        topLinkText : options.back
    });

    $('#menu').hide();
    $('.fg-menu-container')
        .appendTo('#menu_expanded')
        .css({'top': logo_container_height, 'bottom':'auto'});
        //.css({'top': logo_container_height, 'height':max_menu_height, 'bottom':'auto'});

     $("#menu_expanded").width($('.fg-menu-container').outerWidth());

    // Pin / fixed menu
    var onPin = function() {
        desactiveEventsMenu();
        resizePageElements($("#menu_expanded").outerWidth(), true);
        $.cookie('menu_creme', 'expanded', {expires: 7, path: '/', domain: '', secure: false});
    };

    // Unpin / floating menu
    var onUnpin = function() {
        activeEventsMenu();
        resizePageElements($("#menu_collapse").outerWidth(), false);
        $.cookie('menu_creme', 'collapse', {expires: 7, path: '/', domain: '', secure: false});
    };

    // jquery 1.9 migration: toggle(handler, handler, ...) doesn't exist any more.
    if ($.cookie('menu_creme') == 'expanded') {
        $('.pinmenu').addClass('expanded')
        desactiveEventsMenu();
        resizePageElements($("#menu_expanded").outerWidth(), true)
        $("#menu_expanded").show();
        $("#menu_collapse").hide();
    } else {
        activeEventsMenu();
        resizePageElements($("#menu_collapse").outerWidth(), false)
        $("#menu_expanded").hide();
        $("#menu_collapse").show();
    }

    $('.pinmenu').on('click', function() {
        $(this).toggleClass('expanded');

        if ($(this).is('.expanded')) {
            onPin();
        } else {
            onUnpin();
        }
    });

    $("#menu_collapse").css('height', $(document).height());
    $("#menu_expanded").css('height', $(document).height());

    // jquery 1.9.x upgrade.
    $('#menu_expanded').on('menu-item-selected', '#active-menuitem a', function(e, menu) {
        e.stopImmediatePropagation();
        var href = $(this).prop('href');
        //$.cookie('creme-menu-selected', href);
        creme.utils.goTo(href);
    });

    (function bind_scroll() {
        $(window).scroll(function(){
            var $menu = $('.fg-menu-container');

            if ($(this).scrollTop() > $('#logo_container').outerHeight()){
                $menu.addClass('top_fixed');
                $menu.css("left", -$(window).scrollLeft() + "px");
            }
            else{
                $menu.removeClass('top_fixed');
            }
        });
    })();

    $('#logo_container').one('load', function() {
        //var content_height = $("#content").height()+$("#footer").height()+$("#top").height();//Is better but detailviews has float div so we have a very small height size
        /*var content_height = $(document).height();
        var logo_container_height = $('#logo_container').outerHeight();
        var max_menu_height = content_height - logo_container_height;

        $('.fg-menu-container').css({'top': logo_container_height, 'height':max_menu_height, 'bottom':'auto'});
        $('.fg-menu').css('height', max_menu_height*0.9);
        allUIMenus[0].setMaxHeight(max_menu_height*0.9);
        $('#menu_collapse').height(content_height*0.9);*/

        //var previous_selected = $.cookie('creme-menu-selected');

        var logo_container_height = $('#logo_container').outerHeight(); // Webkit
        $('.fg-menu-container').css({'top': logo_container_height}); // Webkit

        var previous_selected = window.location.pathname;

        if (previous_selected != null) {
            var $initial = $('#menu_expanded div.fg-menu-container').find('[href="'+previous_selected+'"]');
            var $ul = null;

            var li_stack = [];
            var more = true;

            var $li = $initial.parent('li');
            li_stack.push($li);

            var max_deep = 30; // I think the depth of the folder will not go more than 30 (which is already huge)
            var deep = 0;

            while (more && deep <= max_deep) { //Set max deep to avoid max recursion
                var ul = $li.parent('ul');
                $li = ul.parent('li');
                if($li.size() == 0) more = false;
                else li_stack.push($li);
                deep++;
            }

            var now = +new Date;

            for (var i = li_stack.length-1; i > 0; i--) {
                li_stack[i].find('a:first').click();
            }
        }
    });
};