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

(function($) {
"use strict";

creme.utils = creme.utils || {};

creme.utils.comparator = function() {
    if (arguments.length === 0) {
        return creme.utils.compareTo;
    }

    var attributes = Array.from(arguments);

    return function(a, b) {
        for (var i = 0; i < attributes.length; ++i) {
            var key = attributes[i];
            var a_attr = a[key], b_attr = b[key];

            if (a_attr === b_attr) {
                continue;
            }

            return a_attr < b_attr ? -1 : 1;
        }

        return 0;
    };
};

creme.utils.compareTo = function(a, b) {
    return a < b ? -1 : (a > b ? 1 : 0);
};
}(jQuery));
