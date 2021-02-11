/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2021  Hybird

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

creme.widget.AutoSizedTextArea = creme.widget.declare('ui-creme-autosizedarea', {
    options: {
        'min-rows': undefined,
        'max-rows': undefined
    },

    _create: function(element, options) {
        var rows = element.attr('rows');
        var minRows = parseInt(options['min-rows'] || rows);
        var maxRows = parseInt(options['max-rows']);

        this._layout = new creme.layout.TextAreaAutoSize({
            min: !isNaN(minRows) ? minRows : undefined,
            max: !isNaN(maxRows) ? maxRows : undefined
        }).bind(element);

        element.addClass('widget-ready');
    },

    layout: function(element) {
        return this._layout;
    }
});

}(jQuery));
