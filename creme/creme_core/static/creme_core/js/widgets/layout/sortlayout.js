/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

/* istanbul ignore next : already supported by any recent browsers */
/* TODO : remove layout tools */
(function($) {
"use strict";

creme.layout = creme.layout || {};

creme.layout.SortLayout = creme.layout.Layout.sub({
    _init_: function(options) {
        options = $.extend({
            comparator: function(a, b) { return 0; },
            reverse: false
        }, options || {});

        this._super_(creme.layout.Layout, '_init_', options);

        this.comparator(options.comparator);
        this.reverse(options.reverse);

        this.onLayout(this._onLayout);
        this.onAdded(this.layout);
        this.onRemoved(this.layout);
    },

    comparator: function(comparator) {
        if (comparator === undefined) {
            return this._comparator;
        }

        this._comparator = $.proxy(comparator, this);
        return this;
    },

    reverse: function(reverse) {
        return Object.property(this, '_reverse', reverse);
    },

    _onLayout: function(event, container) {
        var sortables = Array.copy(this.children().get());

        try {
            sortables = sortables.sort(this._comparator);
            sortables = this.reverse() ? sortables.reverse() : sortables;
        } catch (e) {}

        sortables.forEach(function(item) {
            container.append($(item).remove());
        });
    }
});
}(jQuery));
