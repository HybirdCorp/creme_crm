/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2025  Hybird

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

creme.widget.ImportField = creme.widget.declare('ui-import-field', {
    _create: function(element, options, cb, sync) {
        this._element = element;

        var isNotSelected = element.find('.import-field-select select').val() === '0';
        element.find('.import-field-details').toggleClass('hidden', isNotSelected);

        element.on('change', '.import-field-select select', this._onColumnSelect.bind(this));
        element.addClass('widget-ready');
    },

    _onColumnSelect: function(e) {
        var isNotSelected = $(e.target).val() === '0';
        this._element.find('.import-field-details').toggleClass('hidden', isNotSelected);
    }
});

}(jQuery));
