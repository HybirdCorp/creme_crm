/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020  Hybird

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

/* require: creme.layout.TextAreaAutoSize */

(function($) {
"use strict";

// TODO: unit test ?
creme.widget.AutoSizedTextArea = creme.widget.declare('ui-creme-autosizedarea', {
    _create: function(element) {
        var rows = element.attr('rows');

        new creme.layout.TextAreaAutoSize(rows === undefined ? {} : {min: rows}).bind(element);

        element.addClass('widget-ready');
    }
});

}(jQuery));
