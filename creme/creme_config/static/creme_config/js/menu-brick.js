/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021-2022  Hybird

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

creme.creme_config = creme.creme_config || {};

/* TODO: unit tests */
creme.creme_config.MenuContainersController = creme.component.Component.sub({
    bind: function(brick) {
        if (this.isBound()) {
            throw new Error('MenuContainersController is already bound');
        }

        var brickElement = brick.element();

        function onSortEventHandler(event) {
            var url = event.item.getAttribute('data-reorderable-menu-container-url');
            if (!url) {
                throw new Error('MenuContainersController: no drag & drop URL found.');
            }

            brick.action('update', url, {}, {target: event.newIndex + 1})
                 .on({
                     fail: function() {
                        console.log('MenuContainersController: error when trying to re-order.');
                        brick.refresh();
                     }
                  })
                 .start();
        };

//        this._containers = new Sortable(
//            brickElement.find('.menu-config-container').get(0),
//            {
//                group: brickElement.attr('id'),
//                animation: 150,
//                onSort: onSortEventHandler
//            }
//        );
        var brickID = brickElement.attr('id');
        this._containers = $.map(
            brickElement.find('.menu-config-container'),
            function(element, index) {
                return new Sortable(
                    element,
                    {
                        group: brickID + '-' + index,
                        animation: 150,
                        onSort: onSortEventHandler
                    }
                );
            }
        );

        this._brick = brick;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});
