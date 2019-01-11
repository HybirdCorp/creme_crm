/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

(function($) {
"use strict";

creme.menu = {};

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
};

creme.menu.openQuickForm = function(element) {
    // Hide the current open menu (since the quick-forms are triggered in the menu)
    $('.ui-creme-navigation-activated').removeClass ('ui-creme-navigation-activated');

    // ...or if there's a need to close all popups: $('.ui-dialog .ui-dialog-content').dialog('close');
    if (creme.menu.currentPopup) {
        creme.menu.currentPopup.close();
    }

    creme.menu.currentPopup = creme.dialogs.form(element.attr('data-href'), {reloadOnSuccess: true}).open();
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
};
}(jQuery));
