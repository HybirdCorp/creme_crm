/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.widget.DynamicInput = creme.widget.declare('ui-creme-dinput', {
    options: {
    },

    _create: function(element, options, cb, sync) {
        element.addClass('widget-ready');
    },

    reload: function(element, url, cb, error_cb, sync) {
        if (cb != undefined) cb(element);
    },

    val: function(element, value) {
        //console.log(element, value, element.val());

        if (value !== undefined)
            return element.val(value).change();

        return element.val();
    },

    clone: function(element) {
        var self = creme.widget.DynamicInput;
        var copy = creme.widget.clone(element);
        return copy;
    }
});
