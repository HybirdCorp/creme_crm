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
        // Save state
        var query = new creme.ajax.Query();
        query.url(this.expandUrl())
             .post(state);
    },

    // TODO: rename argument item
//    _toggleItem: function(item, state) {
    _toggleCType: function(item, state) {
        if (state === undefined) {
            state = !item.is('.customform-config-collapsed');
        }

        // collapse all other items
//        this.items().addClass('customform-config-collapsed');
        this.ctypes().addClass('customform-config-collapsed');

        // toggle item state
        item.toggleClass('customform-config-collapsed', !state);

        // scroll to item if opened
        if (state) {
            creme.utils.scrollTo(item, 200);
        }
    },

//    items: function() {
    ctypes: function() {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
//        return this._brick.element().find('.customform-config-item');
        return this._brick.element().find('.customform-config-ctype');
    },

    // Only used by unit tests
//    item: function(id) {
    ctype: function(id) {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
        return this._brick.element()
//                          .find('.customform-config-show-details[data-ct-id="${id}"]:first'.template({id: id}))
                          .find('.customform-config-show-details[data-ct-id="${id}"]'.template({id: id}))
                          .first()
//                          .parents('.customform-config-item:first');
                          .parents('.customform-config-ctype').first();
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'FormGroupsController is already bound');

        this._brick = brick;

//        var toggleItem = this._toggleItem.bind(this);
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
//            toggleItem($(this).parents('.customform-config-item:first'), true);
            toggleCType($(this).parents('.customform-config-ctype').first(), true);
            saveState({ct_id: $(this).data('ct-id')});
        });

        element.on('click', '.customform-config-hide-details', function(e) {
            e.preventDefault();
//            toggleItem($(this).parents('.customform-config-item:first'), false);
            toggleCType($(this).parents('.customform-config-ctype').first(), false);
            saveState({ct_id: '0'});
        });

        element.on('click', '.toggle-icon-container', function(e) {
            e.stopPropagation();

            var icon = $(this);
            var expand = icon.is('.toggle-icon-expand');

            icon.parents('.customform-config-item')
                .first()
                .toggleClass('customform-config-item-collapsed', !expand);
        });

        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
