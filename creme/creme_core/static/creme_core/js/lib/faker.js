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

function __import(module, path) {
    var output = module;
    var pwd = [];
    var splitPath = Array.isArray(path) ? path : path.split('.');

    splitPath.forEach(function(key) {
        Assert.that(key in output, '"${key}" is not a property of ${pwd}', {
            key: key,
            pwd: String(module) + (Object.isEmpty(pwd) ? '' : '.' + pwd.join('.'))
        });

        output = output[key];
        pwd.push(key);
    });

    return output;
}

function __export(module, path, value) {
    var splitPath = path.split('.');
    var target = __import(module, splitPath.slice(0, splitPath.length - 1));

    target[splitPath[splitPath.length - 1]] = value;
};

window.FunctionFaker = function(options) {
    if (Object.isFunc(options)) {
        options = {
            instance: null,
            method: options
        };
    } else {
        options = options || {};
    }

    var method = options.method || function() {};
    var origin = null;
    var property = null;
    var follow = options.follow || false;

    if (Object.isFunc(method)) {
        origin = method;
    } else if (Object.isString(method)) {
        property = method;
        origin = __import(options.instance || window, method);
    } else {
        throw new Error('"${method}" is not a function nor a path'.template({method: method}));
    }

    Assert.that(Object.isFunc(origin), '"${method}" is not a function', {method: method});

    this._calls = [];

    this._instance = options.instance;
    this._origin = origin;
    this._property = property;
    this._follow = follow;
    this.callable = options.callable;
    this.result = options.result;
};

/* globals FunctionFaker */
FunctionFaker.prototype = {
    reset: function() {
        this._calls = [];
        return this;
    },

    called: function() {
        return this._calls.length > 0;
    },

    calls: function(mapper) {
        if (Object.isFunc(mapper)) {
            return this._calls.map(mapper);
        } else {
            return this._calls.slice();
        }
    },

    count: function() {
        return this._calls.length;
    },

    _makeWrapper: function() {
        var faker = this;

        return function() {
            var args = Array.from(arguments);
            faker._calls.push(args);

            if (faker._follow) {
                return faker._origin.apply(faker._instance, args);
            } else if (Object.isFunc(faker.callable)) {
                return faker.callable.apply(faker._instance, args);
            } else {
                return faker.result;
            }
        };
    },

    wrap: function() {
        if (this._wrapper === undefined) {
            this._wrapper = this._makeWrapper().bind(this._instance);

            if (this._property) {
                __export(this._instance || window, this._property, this._wrapper);
            }
        }

        return this._wrapper;
    },

    unwrap: function() {
        if (this._wrapper) {
            if (this._property) {
                __export(this._instance || window, this._property, this._origin);
            }

            delete this._wrapper;
        }

        return this;
    },

    'with': function(callable) {
        try {
            callable(this, this.wrap());
        } finally {
            this.unwrap();
        }

        return this;
    }
};


window.PropertyFaker = function(options) {
    options = options || {};

    Assert.not(Object.isNone(options.instance), 'Cannot fake property of undefined or null');

    this._instance = options.instance;
    this._properties = options.props || {};
};

/* globals PropertyFaker */
PropertyFaker.prototype = {
    'with': function(callable) {
        var origin = {};
        var fakes = {};
        var newKeys = [];
        var instance = this._instance;

        for (var key in this._properties) {
            var prop = Object.getOwnPropertyDescriptor(instance, key);
            var fake = {
                value: this._properties[key],
                writable: false,
                enumerable: false,
                configurable: true
            };

            if (prop === undefined) {
                newKeys.push(key);
            } else {
                origin[key] = prop;

                fake.writable = prop.writable;
                fake.enumerable = prop.enumerable;
                fake.configurable = prop.configurable;
            }

            fakes[key] = fake;
        }

        try {
            Object.defineProperties(instance, fakes);
            callable(this);
        } finally {
            Object.defineProperties(instance, origin);
            newKeys.forEach(function(key) {
                delete instance[key];
            });
        }

        return this;
    }
};


window.DateFaker = function(value) {
    Assert.that(
        Object.isString(value) || Object.isSubClassOf(value, Date),
        'The value must be either a string or a Date',
        {value: value}
    );

    try {
        if (Object.isString(value)) {
            this.frozen = new Date(value).toISOString();
        } else {
            this.frozen = value.toISOString();
        }
    } catch (e) {
        throw new Error('The value "${value}" is not a valid date'.template({value: value}));
    }
};

window.DateFaker.prototype = {
    'with': function(callable) {
        var NativeDate = window.Date;
        var frozen = this.frozen;

        try {
            window.Date = function(value) {
                if (arguments.length > 1) {
                    // This hack allows to call new Date with an array of arguments.
                    // It is really tricky but do the job since ECMAScript 5+
                    var D = NativeDate.bind.apply(NativeDate, [null].concat(Array.from(arguments)));
                    return new D();
                }

                return new NativeDate(value || frozen);
            };

            window.Date.now = function() {
                return new NativeDate(frozen);
            };

            window.Date.parse = NativeDate.parse;
            window.Date.UTC = NativeDate.UTC;

            callable(this);
        } finally {
            window.Date = NativeDate;
        }

        return this;
    }
};

}());
