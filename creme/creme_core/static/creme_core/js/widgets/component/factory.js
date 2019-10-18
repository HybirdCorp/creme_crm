/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2019  Hybird

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

creme.component = creme.component || {};

creme.component.FactoryRegistry = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            strict: false,
            fallback: '_build_',
            builders: {}
        }, options || {});

        this._strict = options.strict || false;
        this._builders = {};

        this.fallback(options.fallback);
        this.registerAll(options.builders);
    },

    fallback: function(fallback) {
        if (fallback === undefined) {
            return this._fallback;
        }

        if (Object.isFunc(fallback)) {
            this._fallbackPrefix = null;
            this._fallback = fallback.bind(this);
        } else if (Object.isString(fallback) && Object.isEmpty(fallback) === false) {
            this._fallbackPrefix = fallback;
            this._fallback = function(key) {
                key = key.replace(/\-/g, '_').toLowerCase();
                return this[fallback + key];
            }.bind(this);
        } else if (fallback === null) {
            this._fallbackPrefix = null;
            this._fallback = null;
        } else {
            throw new Error("invalid fallback builder", fallback);
        }

        return this;
    },

    registerAll: function(builders) {
        builders = builders || {};
        var registered = [];

        if (Object.isString(builders) || Array.isArray(builders)) {
            throw new Error("builders data must be a dict", builders);
        }

        for (var key in builders) {
            try {
                this.register(key, builders[key]);
                registered.push(key);
            } catch (e) {
                // rollback registered actions
                registered.forEach(function(key) {
                                       delete this._builders[key];
                                   }.bind(this));

                throw e;
            }
        }

        return this;
    },

    register: function(key, builder) {
        if (this._builders[key] !== undefined) {
            throw new Error('builder "%s" is already registered'.format(key));
        }

        if (!Object.isFunc(builder)) {
            throw new Error('builder "%s" is not a function'.format(key));
        }

        this._builders[key] = builder;
        return this;
    },

    unregister: function(key) {
        if (this._builders[key] === undefined) {
            throw new Error('builder "%s" is not registered'.format(key));
        }

        delete this._builders[key];
        return this;
    },

    builders: function() {
        return Object.keys(this._builders);
    },

    fallbackBuilders: function() {
        var prefix = this._fallbackPrefix;

        if (Object.isEmpty(prefix) === false) {
            return Object.entries(this).filter(function(e) {
                                            return e[0].startsWith(prefix) && Object.isFunc(e[1]);
                                        }).map(function(e) {
                                            return e[0].slice(prefix.length);
                                        });
        } else {
            return [];
        }
    },

    has: function(key) {
        return Object.isFunc(this.get(key, false));
    },

    get: function(key, strict) {
        strict = (strict === undefined) ? this._strict : strict;
        var builder = this._builders[key];

        if (!Object.isFunc(builder) && Object.isFunc(this._fallback)) {
            builder = this._fallback(key);
        }

        if (Object.isFunc(builder)) {
            return builder.bind(this);
        } else if (strict) {
            throw new Error('no such builder "' + key + '"');
        }
    }
});

}(jQuery));
