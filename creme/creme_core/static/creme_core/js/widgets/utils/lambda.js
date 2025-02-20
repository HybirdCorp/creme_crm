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

creme.utils.Lambda = creme.component.Component.sub({
    _init_: function(callable, parameters) {
        this.lambda(callable, parameters);
    },

    isValid: function() {
        return !Object.isNone(this._lambda);
    },

    apply: function(context, parameters) {
        if (this._lambda) {
            return this._lambda.apply(context, parameters);
        }
    },

    call: function() {
        if (this._lambda) {
            var args = Array.from(arguments);
            return this._lambda.apply(args[0], args.slice(1));
        }
    },

    invoke: function() {
        return this._lambda ? this._lambda.apply(this._context || {}, arguments) : undefined;
    },

    constant: function(value) {
        this._lambda = function() { return value; };
        return this;
    },

    lambda: function(callable, parameters) {
        if (callable === undefined) {
            return this._lambda;
        }

        if (Object.isFunc(callable)) {
            this._lambda = callable;
            return this;
        }

        if (!Object.isType(callable, 'string')) {
            return this.constant(callable);
        }

        if (Object.isEmpty(callable)) {
            throw Error('empty lambda script');
        }

        parameters = Array.isArray(parameters) ? parameters.join(',') : (parameters || '');
        var body = callable.indexOf('return') !== -1 ? callable : 'return ' + callable + ';';

        // eslint-disable-next-line no-new-func, no-eval
        this._lambda = new Function(parameters, body);

        return this;
    },

    callable: function() {
        if (this._lambda) {
            return this._context ? this._lambda.bind(this._context) : this._lambda;
        }
    },

    bind: function(context) {
        this._context = context;
        return this;
    }
});

creme.utils.lambda = function(callable, parameters, defaults) {
    try {
        return new creme.utils.Lambda(callable, parameters).callable();
    } catch (e) {
        if (defaults !== undefined) {
            return defaults;
        } else {
            throw e;
        }
    }
};
}(jQuery));
