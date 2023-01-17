/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2023  Hybird

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

creme.widget.DynamicInput = creme.widget.declare('ui-creme-dinput', {
    options: {
        datatype: 'string'
    },

    _create: function(element, options, cb, sync) {
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        if (!this._enabled) {
            $(element).attr('disabled', '');
        }

        this.reload(element, {}, cb, cb);
        element.addClass('widget-ready');
    },

    _updateDisabledState: function(element) {
        element.toggleProp('disabled', !this._enabled);
    },

    dependencies: function(element) {
        return [];
    },

    reload: function(element, data, cb, error_cb, sync) {
        creme.object.invoke(cb, element);
    },

    reset: function(element) {
        this.val(element, null);
    },

    val: function(element, value) {
        if (value === undefined) {
            return element.val();
        }

        if (!Object.isNone(value) && !Object.isString(value)) {
            value = JSON.stringify(value);
        }

        element.val(value);
        element.prop('disabled', false);
        element.trigger('change');

        this._updateDisabledState(element);
    },

    cleanedval: function(element) {
        var value = this.val(element);

        if (this.options.datatype === 'string') {
            return value;
        }

        return creme.widget.cleanval(value, value);
    }
});

}(jQuery));
