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
        this._options = options || {};

        if (!this._options.expandUrl) {
            throw new Error('FormGroupsController: expandUrl is not set');
        }
    },

    bind: function(brick) {
        if (this.isBound()) {
            throw new Error('FormGroupsController is already bound');
        }

        var brickElement = brick.element();

        brickElement.find('.customform-config-blocks').sortable({
            update: function (e, ui) {
                var url = ui.item.attr('data-reorderable-form-group-url');

                // TODO: do not reload on success ?
                //    .on({
                //        done: function() { ... },
                //        fail: function() { brick.refresh(); }
                //     })
                brick.action('update', url, {}, {target: ui.item.index()})
                     .start();
            }
        });

        var expandUrl = this._options.expandUrl;

        // TODO: real actions instead ?
        brickElement.find('.customform-config-show-details').on('click', function(event) {
            var aTag = $(this);
            var parent = aTag.parents('.customform-config-item').first();
            var oldTop = parent.position().top;

            // Collapses the current expended CType, expands the clicked CType.
            brickElement.find('.customform-config-item.customform-config-expanded')
                        .removeClass('customform-config-expanded')
                        .addClass('customform-config-collapsed');
            aTag.parents('.customform-config-item')
                .removeClass('customform-config-collapsed')
                .addClass('customform-config-expanded');

            // Save state
            creme.ajax.post({
                url: expandUrl,
                data: {ct_id: aTag.attr('data-ct-id')}
            });

            // As we potentially collapse another CType which ban be before and higher, the newly
            // expanded CType can be badly positioned ; we compute the offset between the old and
            // the new positions of the expanded CType, and scroll by this offset.
            window.scrollTo(window.scrollX, window.scrollY + parent.position().top - oldTop);

            event.stopImmediatePropagation();
            return false;
        });

        brickElement.find('.customform-config-hide-details').on('click', function(event) {
            // Collapses the current expended CType
            // TODO: factorise ?
            brickElement.find('.customform-config-item.customform-config-expanded')
                        .removeClass('customform-config-expanded')
                        .addClass('customform-config-collapsed');

            // Save state
            creme.ajax.post({
                url: expandUrl,
                data: {ct_id: '0'}
            });

            event.stopImmediatePropagation();
            return false;
        });

        this._brick = brick;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
