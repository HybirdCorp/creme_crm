/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.widget.CONTAINER_LAYOUTS = {
    'column': function(options) {
        options = options || {};
        var count = options['column-count'] || 1;
        var size = options['column-size'];
        var orderby = Object.isEmpty(options['sort-by']) ? undefined : options['sort-by'];
        var comparator = orderby ? function(a, b) { return $(a).attr(orderby).localeCompare($(b).attr(orderby)); } : undefined;

        return new creme.layout.ColumnSortLayout({
            columns: Object.isEmpty(size) ? count : size,
            resizable: options.resizable,
            comparator: comparator
        });
    },

    'sort': function(options) {
        options = options || {};
        var orderby = Object.isEmpty(options['sort-by']) ? undefined : options['sort-by'];

        if (orderby === undefined) { return null; }

        var comparator = function(a, b) { return $(a).attr(orderby).localeCompare($(b).attr(orderby)); };

        return new creme.layout.SortLayout({
            comparator: comparator,
            reverse: options['sort-reverse']
        });
    }
};

creme.widget.Container = creme.widget.declare('ui-creme-container', {
    options: {
        layout:         'none',
        'sort-by':      '',
        'sort-reverse': false,
        'column-count': 1,
        'column-size':  undefined,
        'resizable':    false
    },

    _create: function(element, options, cb, sync) {
        options['sort-reverse'] = creme.object.isTrue(options['sort-reverse']) || element.is('[sort-reverse]');
        options.resizable = creme.object.isTrue(options.resizable) || element.is('[resizable]');

        var layout_builder = creme.widget.CONTAINER_LAYOUTS[options.layout];
        var layout = Object.isFunc(layout_builder) ? layout_builder(options) : undefined;

        this.layout(element, layout);
        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        if (this._layout !== undefined) {
            this._layout.unbind(element);
        }
    },

    layout: function(element, layout) {
        if (layout === undefined) { return this._layout; }

        if (this._layout !== undefined) {
            this._layout.unbind(element);
        }

        this._layout = layout;
        this._layout.bind(element).layout();
    }
});

}(jQuery));
