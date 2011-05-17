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

creme.widget.DateRange = creme.widget.declare('ui-creme-daterange', {
    options: {
    },

    _get_end: function(element) {
        return $('.date-end', element);
    },

    _get_start: function(element) {
        return $('.date-start', element);
    },

    _get_type: function(element) {
        return $('.range-type', element);
    },

    _create: function(element, options, cb, sync) {
        var self = creme.widget.DateRange;

        self._get_type(element).bind('change', function() {
                if ($(this).val()) {
                    self._get_start().parent().hide();
                    self._get_end().parent().hide();
                } else {
                    self._get_start().parent().show();
                    self._get_end().parent().show();
                }
            }).change();
        element.addClass('widget-ready');
    }
});