/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2021  Hybird

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

creme.creme_config = creme.creme_config || {};

// TODO: unit test
creme.creme_config.FormGroupsController = creme.component.Component.sub({
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

    _toggleItem: function(item, state) {
        if (state === undefined) {
            state = !item.is('.customform-config-collapsed');
        }

        // collapse all other items
        this.items().addClass('customform-config-collapsed');

        // toggle item state
        item.toggleClass('customform-config-collapsed', !state);

        // scroll to item if opened
        if (state) {
            creme.utils.scrollTo(item, 200);
        }
    },

    items: function() {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
        return this._brick.element().find('.customform-config-item');
    },

    item: function(id) {
        Assert.that(this.isBound(), 'FormGroupsController is not bound');
        return this._brick.element()
                          .find('.customform-config-show-details[data-ct-id="${id}"]:first'.template({id: id}))
                          .parents('.customform-config-item:first');
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'FormGroupsController is already bound');

        this._brick = brick;

        var toggleItem = this._toggleItem.bind(this);
        var saveState = this._saveState.bind(this);
        var element = brick.element();

        element.find('.customform-config-blocks').sortable({
            update: function (e, ui) {
                var url = ui.item.data('reorderable-form-group-url');

                var query = new creme.ajax.Query();
                query.url(url)
                     .onFail(function() { brick.refresh(); })
                     .post({
                         target: ui.item.index()
                      });
            }
        });

        element.on('click', '.customform-config-show-details', function(e) {
            e.preventDefault();
            toggleItem($(this).parents('.customform-config-item:first'), true);
            saveState({ct_id: $(this).data('ct-id')});
        });

        element.on('click', '.customform-config-hide-details', function(e) {
            e.preventDefault();
            toggleItem($(this).parents('.customform-config-item:first'), false);
            saveState({ct_id: '0'});
        });

        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
