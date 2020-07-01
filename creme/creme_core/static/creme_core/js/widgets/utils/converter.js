/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2020  Hybird

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

        return this.converter(options.from, options.to)(data, options);
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
            var args = Array.copy(arguments).slice(1);

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

function __toInt(value, options) {
    if (Object.isEmpty(value) && options.empty) {
        return;
    }

    var res = Object.isString(value) ? parseInt(value) : value;
    Assert.not(isNaN(res), '"${value}" is not an integer', {value: value});
    return res;
};

function __toFloat(value, options) {
    if (Object.isEmpty(value) && options.empty) {
        return;
    }

    var res = Object.isString(value) ? parseFloat(value) : value;
    Assert.not(isNaN(res), '"${value}" is not a number', {value: value});
    return res;
};

function __fromJSON(value, options) {
    if (Object.isEmpty(value) && options.empty) {
        return {};
    }

    return creme.utils.JSON.clean(value);
};

function __toJSON(value) {
    return $.toJSON(value);
};

function __toString(value) {
    return String(value);
};

function __momentToIso8601(value, options) {
    if (Object.isNone(value) && options.empty) {
        return '';
    }

    Assert.isAnyOf(value, [moment, Date], '${value} is not a date nor datetime', {value: value});
    return moment(value).format();
};

function __momentToIso8601Date(value, options) {
    if (Object.isNone(value) && options.empty) {
        return '';
    }

    Assert.isAnyOf(value, [moment, Date], '${value} is not a date nor datetime', {value: value});
    return moment(value).format('YYYY-MM-DD');
};

function __iso8601ToMoment(value, options) {
    if (Object.isEmpty(value) && options.empty) {
        return;
    }

    var res = Assert.notThrown(function() {
        return value instanceof moment ? value : moment(value, moment.HTML5_FMT.DATETIME_LOCAL_SECONDS, true);
    }, '"${value}" is not an iso8601 datetime', {value: value});

    Assert.that(res.isValid(), '"${value}" is not an iso8601 datetime', {value: value});
    return res;
};

function __iso8601ToMomentDate(value, options) {
    if (Object.isEmpty(value) && options.empty) {
        return;
    }

    var res = Assert.notThrown(function() {
        return value instanceof moment ? value : moment(value, moment.HTML5_FMT.DATE);
    }, '"${value}" is not an iso8601 datetime', {value: value});

    Assert.that(res.isValid(), '"${value}" is not an iso8601 date', {value: value});
    return res;
};

function __toRGBColor(value, options) {
    var isEmpty = Object.isEmpty(value);

    if (isEmpty && options.empty) {
        return;
    }

    Assert.not(isEmpty, '"${value}" is not a RGB hexadecimal value', {value: String(value)});
    return new RGBColor(value);
};

function __fromRGBColor(value, options) {
    if (Object.isNone(value) && options.empty) {
        return '';
    }

    Assert.is(value, RGBColor, '${value} is not a RGBColor', {value: value});
    return value.toString();
};

__registry.register(['string', 'text'], {
    int: __toInt,
    integer: __toInt,
    float: __toFloat,
    number: __toFloat,
    json: __fromJSON,
    date: __iso8601ToMomentDate,
    datetime: __iso8601ToMoment,
    'datetime-local': __iso8601ToMoment,
    'color': __toRGBColor
});

__registry.register(['number', 'int', 'integer', 'float', 'decimal'], {
    string: __toString,
    text: __toString,
    json: __toJSON
});

__registry.register('date', {
    string: __momentToIso8601Date,
    text: __momentToIso8601Date,
    json: function(value, options) {
        return __toJSON(__momentToIso8601Date(value, options), options);
    }
});

__registry.register(['datetime', 'datetime-local'], {
    string: __momentToIso8601,
    text: __momentToIso8601,
    json: function(value, options) {
        return __toJSON(__momentToIso8601(value, options), options);
    }
});

__registry.register('json', {
    string: __toJSON,
    text: __toJSON
});

__registry.register('color', {
    string: __fromRGBColor,
    text: __fromRGBColor
});

}(jQuery));
