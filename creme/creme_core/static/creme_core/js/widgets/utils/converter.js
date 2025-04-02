/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

creme.utils = creme.utils || {};

var __key = function(from, to) {
    return [String(from), String(to)].join('-');
};

var __ident = function(value) {
    return value;
};

creme.utils.ConverterRegistry = creme.component.Component.sub({
    _init_: function() {
        this._converters = {};
    },

    convert: function(data, options) {
        options = options || {};

        if (options.defaults !== undefined) {
            try {
                this.convert(data, {from: options.from, to: options.to});
            } catch (e) {
                return options.defaults;
            }
        }

        return this.converter(options.from, options.to)(data);
    },

    available: function(from, to) {
        return (from === to) || this._converters[__key(from, to)] !== undefined;
    },

    converter: function(from, to) {
        if (from === to) {
            return __ident;
        }

        var key = __key(from, to);
        var conv = this._converters[key];

        Assert.that(Object.isFunc(conv),
                    '"${key}" is not registered', {key: key});

        return conv;
    },

    register: function(from, to, converter) {
        if (arguments.length === 2) {
            for (var k in to) {
                this.register(from, k, to[k]);
            }

            return this;
        }

        if (Array.isArray(from)) {
            var args = Array.from(arguments).slice(1);

            from.forEach(function(f) {
                this.register.apply(this, [f].concat(args));
            }.bind(this));
        }

        var key = __key(from, to);

        Assert.that(Object.isFunc(converter),
                    '"${key}" converter must be a function', {key: key});

        Assert.not(Object.isFunc(this._converters[key]),
                   '"${key}" is already registered', {key: key});

        this._converters[key] = converter;
        return this;
    },

    unregister: function(from, to) {
        var key = __key(from, to);

        Assert.that(Object.isFunc(this._converters[key]),
                    '"${key}" is not registered', {key: key});

        delete this._converters[key];
        return this;
    }
});

var __registry = new creme.utils.ConverterRegistry();

creme.utils.converters = function() {
    return __registry;
};

creme.utils.convert = function(data, options) {
    return __registry.convert(data, options);
};

var __toInt = function(value) {
    var res = Object.isString(value) ? parseInt(value) : value;
    Assert.not(isNaN(res), '"${value}" is not an integer', {value: value});
    return res;
};

var __toFloat = function(value) {
    var res = Object.isString(value) ? parseFloat(value) : value;
    Assert.not(isNaN(res), '"${value}" is not a number', {value: value});
    return res;
};

var __fromJSON = function(value) {
    return JSON.parse(value);
};

var __toJSON = function(value) {
    return JSON.stringify(value);
};

var __toString = function(value) {
    return String(value);
};

var __toIso8601 = function(value) {
    Assert.isAnyOf(value, [moment, Date], '${value} is not a date nor datetime', {value: value});
    return moment(value).format();
};

var __toIso8601Date = function(value) {
    Assert.isAnyOf(value, [moment, Date], '${value} is not a date nor datetime', {value: value});
    return moment(value).format('YYYY-MM-DD');
};

var __fromIso8601 = function(value) {
    var res = Assert.notThrown(function() {
        return value instanceof moment ? value : moment(value);
    }, '"${value}" is not an iso8601 datetime', {value: value});

    Assert.that(res.isValid(), '"${value}" is not an iso8601 datetime', {value: value});
    return res;
};

var __fromIso8601Date = function(value) {
    var res = Assert.notThrown(function() {
        return value instanceof moment ? value : moment(value, moment.HTML5_FMT.DATE);
    }, '"${value}" is not an iso8601 datetime', {value: value});

    Assert.that(res.isValid(), '"${value}" is not an iso8601 date', {value: value});
    return res;
};

__registry.register(['string', 'text'], {
    int: __toInt,
    integer: __toInt,
    float: __toFloat,
    number: __toFloat,
    json: __fromJSON,
    date: __fromIso8601Date,
    datetime: __fromIso8601
});

__registry.register(['number', 'int', 'integer', 'float'], {
    string: __toString,
    text: __toString,
    json: __toJSON
});

__registry.register('date', {
    string: __toIso8601Date,
    text: __toIso8601Date,
    json: function(value) {
        return __toJSON(__toIso8601Date(value));
    }
});

__registry.register('datetime', {
    string: __toIso8601,
    text: __toIso8601,
    json: function(value) {
        return __toJSON(__toIso8601Date(value));
    }
});

__registry.register('json', {
    string: __toJSON,
    text: __toJSON
});

}(jQuery));
