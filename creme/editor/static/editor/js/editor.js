/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2024  Hybird

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

creme.widget.CKEditor = creme.widget.declare('ui-creme-ckeditor', {
    options: {},

    _create: function(element, options, cb, sync) {
        this._editor = new creme.form.CKEditor(element, options || {});

        this._editor.ckeditorSetup().then(function() {
            creme.object.invoke(cb, element);
            element.addClass('widget-ready');
        });
    },

    _destroy: function(element) {
        if (this._editor) {
            this._editor.destroy();
        }
    },

    editor: function(element) {
        return this._editor;
    }
});

}(jQuery));
