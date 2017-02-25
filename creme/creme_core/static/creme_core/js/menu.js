/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2017  Hybird

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


// Old menu API ----------------------------------------------------------------
creme.menu.NavIt = function(trigger_selector, options, listeners) {
    var options = options || {};
    var listeners = listeners || {};

    $(trigger_selector).NavIt(options);
    $(trigger_selector).find('a').click(function(e) {
        e.preventDefault();

        var $a = $(this);
        var confirm = $a.hasClass('confirm');
        var action  = $a.hasClass('post') ? 'post' : 'get';
        var ajax    = $a.hasClass('ajax');
        var url     = $a.prop('href');

        if (ajax) {
            var queryOptions = $.extend({action:action, link:$a}, options.queryOptions || {});

            if (confirm) {
                creme.utils.confirmAjaxQuery(url, queryOptions)
                           .on(listeners).start();
            } else {
                creme.utils.ajaxQuery(url, queryOptions)
                           .on(listeners).start();
            }
        } else {
            if (confirm) {
                creme.utils.confirmBeforeGo(url, ajax, opts);
            } else {
                creme.utils.goTo(url);
            }
        }
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

    var logo_container_height = $('#logo_container').outerHeight();
    var height = $('#menu_expanded').outerHeight();

    $('#menu').menu({
        content: $('#tree_menu2').html(),
        flyOut: false,
        backLink: false,
        alwaysOpen: true,
        maxHeight: height,
        crumbDefaultText: options.title,
        topLinkText: options.back
    });

    $('#menu').hide();
    $('.fg-menu-container')
        .appendTo('#menu_expanded')
        .css({'top': logo_container_height, 'bottom':'auto'});

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
}


// New menu API ----------------------------------------------------------------

creme.menu.bindEvents = function() {
    var menu = $('.ui-creme-navigation');
    var items = menu.children('li');

    // Activate menus on hover events
    items.hover(function(e) {
        $(this).addClass('ui-creme-navigation-activated');
    }, function(e) {
        $(this).removeClass('ui-creme-navigation-activated');
    });

    // Activate menus when clicked directly (for devices without hover)
    items.click(function(e) { // possibly limit this to touch press events for tablets, or maybe just disable for desktop ?
        if (e.target != this) return; // when clicking on sub-menu entries (<a>s inside <li>s inside <ul>s inside the <li> menu) we don't want to do anything

        var currentActivatedItem = menu.children('li.ui-creme-navigation-activated');
        var itemToActivate = $(e.currentTarget);

        if (currentActivatedItem.length > 0 && currentActivatedItem.index() != itemToActivate.index()) {
            currentActivatedItem.removeClass('ui-creme-navigation-activated');
//          menu.removeClass ('ui-creme-navigation-activated'); // for the different background color on hovered items effect, when there is one activated submenu already
        }

        if (currentActivatedItem.length == 0 || currentActivatedItem.index() != itemToActivate.index()) {
            itemToActivate.addClass('ui-creme-navigation-activated');
//          menu.addClass ('ui-creme-navigation-activated'); // for the different background color on hovered items effect, when there is one activated submenu already
        }
    });
}

creme.menu.openQuickForm = function(element) {
//    var uri = '/creme_core/quickforms/%s/%s';
//    var type = element.attr('data-ct-id');
//    var count = element.attr('data-entity-count') || 1;

    // Hide the current open menu (since the quick-forms are triggered in the menu)
    $('.ui-creme-navigation-activated').removeClass ('ui-creme-navigation-activated');

    // ...or if there's a need to close all popups: $('.ui-dialog .ui-dialog-content').dialog('close');
    if (creme.menu.currentPopup)
        creme.menu.currentPopup.close();

//    creme.menu.currentPopup = creme.dialogs.form(uri.format(type, count), {reloadOnSuccess: true}).open();
    creme.menu.currentPopup = creme.dialogs.form(element.attr('href'), {reloadOnSuccess: true}).open();
}

creme.menu.openCreateAnyDialog = function(a_tag) {
    // Hide the current open menu (since the quick-forms are triggered in the menu)...
    $('.ui-creme-navigation-activated').removeClass('ui-creme-navigation-activated');

    // ...or if there's a need to close all popups: $('.ui-dialog .ui-dialog-content').dialog('close');
    if (creme.menu.currentPopup)
        creme.menu.currentPopup.close();

    var grouped_links = JSON.parse(a_tag.getAttribute('data-grouped-links'));
    var $content = $('<div>').addClass('create-all-form');
    var max_col = 1;

    for (var j in grouped_links) {
        var grouped_links_row = grouped_links[j];
        var $container = $('<div>').addClass('create-group-container')
                                   .addClass('create-group-container-%s-columned'.format(grouped_links_row.length))
                                   .appendTo($content)
        max_col = Math.max(max_col, grouped_links_row.length);

        for (var i in grouped_links_row) {
            var links_group = grouped_links_row[i];
            var $group = $('<div>').addClass('create-group')
                                   .appendTo($container);

            $('<div>').addClass('create-group-title').text(links_group.label)
                      .appendTo($group);

            var entries = links_group.links;

            for (var i = 0; i < entries.length; ++i) {
                var entry = entries[i];

                if (entry.url !== undefined) {
                    $('<a>').addClass('create-group-entry')
                            .attr('href', entry.url).text(entry.label)
                            .appendTo($group);
                } else {
                    $('<span>').addClass('create-group-entry forbidden')
                               .text(entry.label)
                               .appendTo($group);
                }
            }
        }
    }

    creme.menu.currentPopup = creme.dialogs.html($content[0].outerHTML,
                                                 {title: gettext('Chose the type of entity to create'),
                                                  width: Math.max(550, max_col * 200)
                                                 }
                                                ).open();
}
