/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2024  Hybird

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

/* TODO: Use Select2 widget with "persisting" tag ({tags: true} loses the entry after closing) */
creme.widget.SelectOrInputWidget = creme.widget.declare('ui-creme-selectorinput', {
    _create: function(element, options) {
        var select = element.find('select');
        var input = element.find('input[type="text"]');
        var inputBackup = input.val();

        select.on('change', function(e) {
             if (select.val() === '0') {
                input.val(inputBackup);
             } else {
                inputBackup = input.val();
                input.val('');
             }
        });
        input.on('input keyup paste', function(e) {
            select.val(0);
        });

        element.addClass('widget-ready');
    },

    val: function(element, value) {
        if (value === undefined) {
            value = element.find('select').val();
            return (value === '0') ? element.find('input[type="text"]').val() : value;
        }

        if (!Object.isNone(value) && !Object.isString(value)) {
            value = JSON.stringify(value);
        }

        element.find('select').val(value).trigger('change');
    }
});

}(jQuery));
