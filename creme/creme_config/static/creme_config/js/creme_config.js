/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020  Hybird

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
    },

    bind: function(brick) {
        if (this.isBound()) {
            throw new Error('FormGroupsController is already bound');
        }

        brick.element().find(".customform-config-blocks").sortable({
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

        this._brick = brick;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
