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

creme.utils = creme.utils || {};

creme.utils.ConverterRegistry = function() {
    this._init_();
}

creme.utils.ConverterRegistry.prototype = {
    _init_: function() {
        this._converters = {};
    },

    convert: function(from, to, data, defaults)
    {
        if (from === to)
            return data;

        var converter = this.converter(from, to);

        if (!Object.isFunc(converter))
        {
            if (defaults !== undefined)
                return defaults;

            throw new Error('no such converter "' + from + '-' + to + '"');
        }

        try
        {
            return converter.call(this, data);
        } catch(e) {
            if (defaults !== undefined)
                return defaults;

            throw new Error('unable to convert data from "' + from + '" to "' + to + '" : ' + e);
        }
    },

    converter: function(from, to) {
        return this._converters[from + '-' + to];
    },

    register: function(from, to, converter) {
        if (Object.isFunc(this.converter(from, to)))
            throw new Error('converter "' + from + '-' + to + '" is already registered');

        this._converters[from + '-' + to] = converter;
    },

    unregister: function(from, to)
    {
        if (this.converter(from, to) === undefined)
            throw new Error('no such converter "' + from + '-' + to + '"');

        delete this._converters[from + '-' + to];
    }
};

creme.utils.converters = new creme.utils.ConverterRegistry();
creme.utils.converter = $.proxy(creme.utils.converters.converter, creme.utils.converters);
creme.utils.convert = $.proxy(creme.utils.converters.convert, creme.utils.converters);

creme.utils.converters.register('string', 'number', function(value) {
    Object.assertIsTypeOf(value, 'string');

    var num = parseFloat(value);

    if (isNaN(num))
        throw '"' + value + '" is not a number';

    return num;
});

creme.utils.converters.register('string', 'float', creme.utils.converter('string', 'number'));

creme.utils.converters.register('string', 'int', function(value) {
    Object.assertIsTypeOf(value, 'string');

    var num = parseInt(value);

    if (isNaN(num))
        throw '"' + value + '" is not a number';

    return num;
});

