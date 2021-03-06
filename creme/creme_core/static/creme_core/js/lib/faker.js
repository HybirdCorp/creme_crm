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

(function($) {
"use strict";

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
    } else if (Object.isNone(options.instance) === false) {
        property = method;
        origin = options.instance[method];
        Assert.that(Object.isFunc(origin), '"${method}" is not a method property', {method: method});
    } else {
        throw new Error('"${method}" is not a function'.template({method: method}));
    }

    this._calls = [];

    this._instance = options.instance;
    this._origin = origin;
    this._property = property;
    this._follow = follow;
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

    calls: function() {
        return this._calls.slice();
    },

    count: function() {
        return this._calls.length;
    },

    _makeWrapper: function() {
        var faker = this;

        return function() {
            var args = Array.copy(arguments);
            faker._calls.push(args);

            if (faker._follow) {
                return faker._origin.call(faker._instance, Array.copy(arguments));
            } else {
                return faker.result;
            }
        };
    },

    wrap: function() {
        if (this._wrapper === undefined) {
            this._wrapper = this._makeWrapper().bind(this._instance);

            if (this._property) {
                this._instance[this._property] = this._wrapper;
            }
        }

        return this._wrapper;
    },

    unwrap: function() {
        if (this._wrapper) {
            if (this._property) {
                this._instance[this._property] = this._origin;
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

}(jQuery));
