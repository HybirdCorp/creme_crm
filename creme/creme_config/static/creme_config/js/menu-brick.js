/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021-2023  Hybird

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

creme.MenuContainersController = creme.component.Component.sub({
    _init_: function(brick) {
        this._brick = brick;

        var brickID = brick.element().attr('id');
        var _onSort = this._onSort.bind(this);

        this._containers = $.map(
            brick.element().find('.menu-config-container'),
            function(element, index) {
                return new Sortable(
                    element, {
                        group: brickID + '-' + index,
                        animation: 150,
                        onSort: _onSort
                    }
                );
            }
        );

        return this;
    },

    _onSort: function(event) {
        var url = $(event.item).data('reorderable-menu-container-url');
        var brick = this._brick;

        brick.action('update', url, {}, {target: event.newIndex + 1})
             .on('fail', function() {
                  console.log('MenuContainersController: error when trying to re-order.');
                  brick.refresh();
              })
             .start();
    }
});

}(jQuery));
