/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

creme.menu.MenuController = creme.component.Component.sub({
    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('MenuController is already bound');
        }

        this._element = element;

        this._initMenuItems(element);
        this._initQuickFormItems(element);
        this._initAnyFormItems(element);

        return this;
    },

    closeMenu: function() {
        // Hide the current open menu (since the quick-forms are triggered in the menu)
        $('.ui-creme-navigation-activated', this._element).removeClass('ui-creme-navigation-activated');
        return this;
    },

    _initMenuItems: function(element) {
        var menu = element.find('.ui-creme-navigation');
        var items = menu.children('li');

        // Activate menus on hover events
        items.on('mouseenter', function(e) {
            $(this).addClass('ui-creme-navigation-activated');
        }).on('mouseleave', function(e) {
            $(this).removeClass('ui-creme-navigation-activated');
        });

        // Activate menus when clicked directly (for devices without hover)
        items.on('click', function(e) { // possibly limit this to touch press events for tablets, or maybe just disable for desktop ?
            if (e.target !== this) {
                return; // when clicking on sub-menu entries (<a>s inside <li>s inside <ul>s inside the <li> menu) we don't want to do anything
            }

            var currentActivatedItem = menu.children('li.ui-creme-navigation-activated');
            var itemToActivate = $(e.currentTarget);
            var isOtherItemActive = currentActivatedItem.index() !== itemToActivate.index();

            if (isOtherItemActive) {
                currentActivatedItem.removeClass('ui-creme-navigation-activated');
                itemToActivate.addClass('ui-creme-navigation-activated');
            }
        });
    },

    _initQuickFormItems: function(element) {
        var openQuickFormDialog = this._openQuickFormDialog.bind(this);

        $('.quickform-menu-link', element).on('click', function(e) {
            e.preventDefault();
            openQuickFormDialog($(this));
        });
    },

    _initAnyFormItems: function(element) {
        var openCreateAnyDialog = this._openCreateAnyDialog.bind(this);

        $('.anyform-menu-link', element).on('click', function(e) {
            e.preventDefault();
            openCreateAnyDialog($(this));
        });
    },

    _openPopup: function(dialog) {
        // ...or if there's a need to close all popups: $('.ui-dialog .ui-dialog-content').dialog('close');
        if (this._activePopup) {
            this._activePopup.close();
            this._activePopup = undefined;
        }

        this._activePopup = dialog.open();
    },

    _openQuickFormDialog: function(item) {
        this.closeMenu();
        this._openPopup(creme.dialogs.form(item.attr('data-href'), {reloadOnSuccess: true}));
    },

    _openCreateAnyDialog: function(item) {
        this.closeMenu();

        // TODO : use cache ?
        var groupedLinks = JSON.parse(item.attr('data-grouped-links'));
        var maxColumnCount = 1;

        groupedLinks.forEach(function(item) {
            maxColumnCount = Math.max(maxColumnCount, item.length);
        });

        var renderLinkGroupRow = function(item) {
            return (
                '<div class="create-group-container create-group-container-${count}-columned">' +
                    '${groups}' +
                '</div>').template({
                    count: item.length,
                    groups: item.map(renderLinkGroup).join('')
                });
        };

        var renderLinkGroup = function(item) {
            return (
                '<div class="create-group">' +
                    '<div class="create-group-title">${title}</div>' +
                    '${links}' +
                '</div>').template({
                    title: item.label,
                    links: item.links.map(renderLink).join('')
                });
        };

        var renderLink = function(link) {
            if (link.url) {
                return '<a href="${url}" class="create-group-entry">${label}</a>'.template(link);
            } else {
                return '<span class="create-group-entry forbidden">${label}</span>'.template(link);
            }
        };

        var html = '<div class="create-all-form">${rows}</div>'.template({
            rows: groupedLinks.map(renderLinkGroupRow).join('')
        });

        this._openPopup(creme.dialogs.html(html, {
                                              title: gettext('Chose the type of entity to create'),
                                              width: Math.max(550, maxColumnCount * 200)
                                           }));
    }
});

}(jQuery));
