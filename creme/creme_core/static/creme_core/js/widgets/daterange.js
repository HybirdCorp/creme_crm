/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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

creme.widget.DateRange = creme.widget.declare('ui-creme-daterange', {
    options: {},

    _create: function(element, options, cb, sync) {
        var self = this;
        var datetype = this.dateType(element);

        datetype.on('change', function() {
            self._onTypeChange(element, $(this).val());
        });

        this._onTypeChange(element, datetype.val());
        element.addClass('widget-ready');
    },

    _onTypeChange: function(element, value) {
        var isCustomRange = Object.isEmpty(value);

        element.find('[data-daterange-field]').each(function() {
            $(this).parents('.daterange-field').first().toggleClass('not-visible', !isCustomRange);
        });

        if (!isCustomRange) {
            element.find('[data-daterange-field]').val('');
        }
    },

    reset: function(element) {
        this.endDate(element).val('');
        this.startDate(element).val('');
        this.dateType(element).val('').trigger('change');
    },

    endDate: function(element) {
        return $('[data-daterange-field="end"]', element);
    },

    startDate: function(element) {
        return $('[data-daterange-field="start"]', element);
    },

    dateType: function(element) {
        return $('[data-daterange-type]', element);
    }
});
}(jQuery));
