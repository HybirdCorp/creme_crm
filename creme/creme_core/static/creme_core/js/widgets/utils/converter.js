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


creme.utils.JSON = function() {}

creme.utils.JSON.prototype = {
    encode: function(data)
    {
        if (typeof jQuery.toJSON !== 'function') {
            throw 'not implemented !';
        }

        return jQuery.toJSON(data);
    },

    isJSON: function(data)
    {
        // Make sure the incoming data is actual JSON
        // Logic borrowed from http://json.org/json2.js
        return typeof data === 'string' && 
               (/^[\],:{}\s]*$/.test(data.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
                                         .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
                                         .replace(/(?:^|:|,)(?:\s*\[)+/g, "")));
    },

    decode: function(data, defaults)
    {
        if (defaults !== undefined) {
            try {
                this.decode(data);
            } catch(e) {
                return defaults;
            }
        }

        if ( typeof data !== "string" || !data) {
            throw 'Invalid data type or empty string';
        }

        // Make sure leading/trailing whitespace is removed (IE can't handle it)
        data = jQuery.trim(data);

        try {
            if (window.JSON && window.JSON.parse)
                return window.JSON.parse(data);
        } catch(err) {
            throw 'JSON parse error: ' + err;
        }

        var isvalid = this.isJSON(data);

        if (!isvalid)
            throw 'JSON parse error (fallback)';

        try {
            // Try to use the native JSON parser first
            return (new Function("return " + data))();
        } catch(err) {
            throw 'JSON parse error (fallback): ' + err;
        }
    }
}

creme.utils.JSON.decoder = function(defaults) {
    return function(data) {creme.utils.JSON.prototype.decode(data, defaults);};
}

creme.utils.JSON.clean = function(data, defaults) {
    return Object.isType(data, 'string') ? creme.utils.JSON.prototype.decode(data, defaults) : data;
}
