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

(function($) {
"use strict";

creme.widget.ScrollActivator = creme.widget.declare('ui-creme-scrollactivator', {
    options: {
        scroll: 'absolute',
        delay: 50
    },

    _scrollBox: function(container) {
        var self = this;

        var box = {
            top:    container.scrollTop(),
            left:   container.scrollLeft(),
            width:  self._isrelative ? container.width() : $(window).width(),
            height: self._isrelative ? container.height() : $(window).height()
        };

        box.bottom = (box.top + box.height);
        box.right = (box.left + box.width);

        return box;
    },

    _collide: function(box, item) {
        var top = this._isrelative ? box.top + item.position().top : item.offset().top;
        var left = this._isrelative ? box.left + item.position().left : item.offset().left;
        var bottom = top + item.height();
        var right = left + item.width();

        var result = !(box.bottom < top || box.top > bottom) &&
                     !(box.left > right || box.right < left);

//        console.log('box [top:', box.top, ', left:', box.left, ', bottom:', box.bottom, ', right:', box.right, '],',
//                    'item [top:', top, ', left:', left, ', bottom:', bottom, ', right:', right, '],',
//                    'collide:', result);

        return result;
    },

    _activables: function(element, container) {
        var self = this;

        if ((element.is(':visible') && self._collide(self._scrollBox($(document)), element)) === false) {
            return;
        }

        var box = self._scrollBox(container);

        return $('.ui-creme-widget:not(.widget-active)', element).filter(function() {
            return self._collide(box, $(this));
        });
    },

    _activateItem: function(item, delay) {
        creme.object.deferred_start(item, 'creme.widget.scrollactivator.activate_item', function() {
            item.creme().create();
        }, delay);
    },

    _activate: function(element) {
        var self = this;

        creme.object.deferred_start(element, 'creme.widget.scrollactivator.activate', function() {
            var activables = self._activables(element, self._container);

            if (activables) {
                activables.each(function(index) { self._activateItem($(this)); });
            }
        }, self._delay);
    },

    _create: function(element, options, cb, sync, attributes) {
        var self = this;
        self._delay = options['delay'];
        self._isrelative = options['scroll'] === 'relative';
        self._container = self._isrelative ? $(element) : $(document);

        self._container.scroll(function() {
            self._activate(element);
        });
        self._activate(element);

        element.addClass('widget-ready');
    }
});

}(jQuery));
