/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

/* //globals BrowserVersion */
(function($) {
"use strict";

creme.layout = creme.layout || {};

creme.layout.TextAreaAutoSize = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({min: 2}, options || {});

        this._min = options.min;
        this._max = options.max;
        this._listeners = this._onResize.bind(this);
    },

    _onResize: function(e) {
        var element = this._delegate;
        var text = element.val();

        /* if bound to several types of event
        if (this._previousValue === text) {
            return;
        }
        this._previousValue = text;
        */

        var previous = this._count !== undefined ? this._count : this._initial;
        var lines = (text !== null) ? text.split('\n') : [];
        var count = lines.length;

        if (e.keyCode === 13) {
            ++count;
        }

        // Large lines management (TODO: cache the results?)
        if (lines) {
            var width = element.width();

            if (width) {
                // TODO: unit test (need not null sizes in test cases)
                var ghostSpan = $('<span></span>');
                ghostSpan.css({
                    // font: element.css('font'),  does not work with FireFox
                    'font-family': element.css('font-family'),
                    'font-size': element.css('font-size'),
                    position: 'absolute',
                    top: -1000,
                    left: -1000
                });

                ghostSpan.appendTo('body');

                for (var i in lines) {
                    ghostSpan.text(lines[i]);
                    count += Math.floor(ghostSpan.width() / width);
                }

                ghostSpan.remove();
            }
        }

        count = Math.max(this._min, count);
        count = !isNaN(this._max) ? Math.min(this._max, count) : count;

        this._count = count;

        if (previous !== count) {
            element.get().scrollTop = 0;
            element.attr('rows', count);
        }
    },

    bind: function(element) {
        if (this._delegate !== undefined) {
            throw new Error('already bound');
        }

        this._delegate = element;
        element.css({'overflow-y': 'hidden', 'resize': 'none'});

        this._initial = parseInt(element.attr('rows')) || 1;
        this._onResize(element);

        element.on('input', this._listeners);
        return this;
    },

    unbind: function() {
        if (this._delegate === undefined) {
            throw new Error('not bound');
        }

        this._delegate.off('input', this._listeners);
        this._delegate = undefined;

        return this;
    }
});
}(jQuery));
