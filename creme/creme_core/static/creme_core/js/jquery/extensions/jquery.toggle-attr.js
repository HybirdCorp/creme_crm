/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021  Hybird

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

$.fn.toggleProp = function(name, enabled, value) {
    return this.each(function() {
        var element = $(this);
        var state = Boolean(element.prop(name));
        var next = enabled !== undefined ? enabled : !state;

        if (value === undefined) {
            element.prop(name, next);
        } else {
            if (next) {
                element.prop(name, value);
            } else {
                element.removeProp(name);
            }
        }
    });
};

$.fn.toggleAttr = function(name, enabled, value) {
    return this.each(function() {
        var element = $(this);
        var state = element.is('[' + name + ']');
        var next = enabled !== undefined ? enabled : !state;

        if (next) {
            element.attr(name, value || element.attr(name) || '');
        } else {
            element.removeAttr(name);
        }
    });
};

}(jQuery));
