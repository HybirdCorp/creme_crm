/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2025  Hybird

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

(function() {
"use strict";

var __eval = function(value) {
    return Object.isFunc(value) ? value() : value;
};

var __isTypeOf = function(value, expected) {
    if (Object.isString(expected)) {
        return Object.isType(value, expected);
    } else if (expected === Array) {
        return Array.isArray(value);
    } else {
        return (value instanceof expected);
    }
};

var __fmtType = function(value) {
    if (Object.isString(value)) {
        return value;
    } else if (value === String) {
        return 'String';
    } else if (value === Array) {
        return 'Array';
    } else if (Object.isFunc(value)) {
        var name = (String(value).match(/function[\s]*(.*)[\s]*\(/) || ['', ''])[1];
        return Object.isEmpty(name) ? value : name + '()';
    } else {
        return String(value);
    }
};

window.Assert = {
    that: function(test, message, context) {
        if (Boolean(__eval(test)) === false) {
            throw new Error((message || 'assertion failed').template(context || {}));
        }
    },

    not: function(test, message, context) {
        if (Boolean(__eval(test)) === true) {
            throw new Error((message || 'assertion failed').template(context || {}));
        }
    },

    notThrown: function(test, message, context) {
        try {
            return test();
        } catch (e) {
            throw new Error((message || '${error}').template(
                Object.assign({error: e.message}, context || {})
            ));
        }
    },

    in: function(value, data, message, context) {
        message = message || "${value} is not in the collection";
        context = Object.assign({}, context || {}, {value: value});

        if (Array.isArray(data) || Object.isString(data)) {
            Assert.that(data.indexOf(value) !== -1, message, context);
        } else {
            Assert.that(value in data, message, context);
        }

        return value;
    },

    notIn: function(value, data, message, context) {
        message = message || "${value} should not be in the collection";
        context = Object.assign({}, context || {}, {value: value});

        if (Array.isArray(data) || Object.isString(data)) {
            Assert.that(data.indexOf(value) === -1, message, context);
        } else {
            Assert.that((value in data) === false, message, context);
        }

        return value;
    },

    is: function(value, expected, message, context) {
        message = message || '${value} is not a ${expected}';
        context = Object.assign({}, context || {}, {
            value: Object.isString(value) ? '"' + value + '"' : value,
            expected: __fmtType(expected)
        });

        Assert.that(__isTypeOf(value, expected), message, context);
        return value;
    },

    isAnyOf: function(value, expected, message, context) {
        message = message || '${value} is none of [${expected}]';
        context = Object.assign({}, context || {}, {
            value: Object.isString(value) ? '"' + value + '"' : value,
            expected: expected.map(__fmtType).join(', ')
        });

        Assert.is(expected, Array, 'expected type list must be an array');

        var matches = expected.filter(function(expected) {
            return __isTypeOf(value, expected);
        });

        Assert.that(matches.length > 0, message, context);
        return value;
    }
};

}());
