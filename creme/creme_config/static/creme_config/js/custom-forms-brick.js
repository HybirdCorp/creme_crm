/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2022  Hybird

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

(function($) {
"use strict";

creme.FormGroupsController = creme.component.Component.sub({
    _init_: function(options) {
        options = options || {};

        Assert.not(Object.isEmpty(options.expandUrl), 'FormGroupsController expandUrl is not set');

        this.expandUrl(options.expandUrl);
    },

    expandUrl: function(url) {
        return Object.property(this, '_expandUrl', url);
    },

    _saveState: function(state) {
        var query = new creme.ajax.Query();
        query.url(this.expandUrl()).post(state);
    },

    _toggleCType: function(element, state) {
        if (state === undefined) {
            state = !element.is('.customform-config-collapsed');
        }

        // Collapse all other ctype containers
        this.ctypes().addClass('customform-config-collapsed');

        element.toggleClass('customform-config-collapsed', !state);

        if (state) {
            // Scroll to element if opened
            creme.utils.scrollTo(element, 200);
        } else {
            // When we hide a ContentType container, the server side loses the
            // information about expanded items.
            element.find('.customform-config-item').addClass('customform-config-collapsed');
        }
    },

    ctypes: function() {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
        return this._brick.element().find('.customform-config-ctype');
    },

    // Only used by unit tests
    ctype: function(id) {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
        return this._brick.element()
                          .find('.customform-config-show-details[data-ct-id="${id}"]'.template({id: id}))
                          .first()
                          .parents('.customform-config-ctype').first();
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'FormGroupsController is already bound');

        this._brick = brick;

        var toggleCType = this._toggleCType.bind(this);
        var saveState = this._saveState.bind(this);
        var element = brick.element();

        element.find('.customform-config-blocks').sortable({
            update: function (e, ui) {
                var url = ui.item.data('reorderable-form-group-url');

                var query = new creme.ajax.Query();
                // NB: we reload the brick on success to keep the edition URLs (which use groups indices/orders)
                query.url(url)
                     .onFail(function() { brick.refresh(); })
                     .onDone(function() { brick.refresh(); })
                     .post({
                         target: ui.item.index()
                      });
            }
        });

        element.on('click', '.customform-config-show-details', function(e) {
            e.preventDefault();
            toggleCType($(this).parents('.customform-config-ctype').first(), true);
            saveState({action: 'show', ct_id: $(this).data('ct-id')});
        });

        element.on('click', '.customform-config-hide-details', function(e) {
            e.preventDefault();
            toggleCType($(this).parents('.customform-config-ctype').first(), false);
            saveState({action: 'hide', ct_id: $(this).data('ct-id')});
        });

        element.on('click', '.toggle-icon-container', function(e) {
            e.stopPropagation();

            var icon = $(this);
            var expand = icon.is('.toggle-icon-expand');

            icon.parents('.customform-config-item')
                .first()
                .toggleClass('customform-config-collapsed', !expand);

            saveState({action: (expand ? 'show' : 'hide'), item_id: $(this).data('item-id')});
        });

        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
