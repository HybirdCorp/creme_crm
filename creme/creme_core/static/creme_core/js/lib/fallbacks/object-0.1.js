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


(function() {
    "use strict";

    function appendStatic(name, method) {
        if (!Object[name]) {
            Object[name] = method;
        }
    };

    appendStatic('property', function(obj, key, value) {
        if (value === undefined) {
            return obj[key];
        }

        obj[key] = value;
        return obj;
    });

    appendStatic('isNone', function(obj) {
        return obj === undefined || obj === null;
    });

    appendStatic('isEmpty', function(obj) {
        if (Object.isNone(obj) || obj.length === 0) {
            return true;
        }

        if (typeof obj === 'number') {
            return false;
        }

        for (var name in obj) {
            return false;
        }

        return true;
    });

    appendStatic('isNotEmpty', function(obj) {
        return !Object.isEmpty(obj);
    });

    appendStatic('isType', function(obj, type) {
        return (typeof obj === type);
    });

    appendStatic('isNumber', function(obj) {
        return (typeof obj === 'number');
    });

    appendStatic('isFunc', function(obj) {
        return (typeof obj === 'function');
    });

    appendStatic('isString', function(obj) {
        /*
         * typeof null === 'object'... WAAAT !
         */
        if (!Object.isNone(obj)) {
            return (typeof obj === 'string') || (obj instanceof String);
        } else {
            return false;
        }
    });

    // TODO : Only used in creme.component.Component : move it there ?
    appendStatic('proxy', function(delegate, context, options) {
        if (Object.isNone(delegate)) {
            return;
        }

        options = options || {};
        context = context || delegate;

        var proxy = {__context__: context};
        var filter = Object.isFunc(options.filter) ? options.filter : function () { return true; };
        var parameters = Object.isFunc(options.arguments) ? function (args) { return options.arguments(Array.from(args)); } : Array.from;

        for (var key in delegate) {
            var value = delegate[key];

            if (!Object.isFunc(value) || filter(key, value) === false) {
                continue;
            }

            // use a function to 'keep' the current loop step context
            (function(proxy, fn, key) {
                proxy[key] = function() {
                    return fn.apply(this.__context__, parameters(arguments));
                };
            })(proxy, value, key);
        }

        return proxy;
    });

    appendStatic('isSubClassOf', function(object, constructor) {
        if (constructor && Object.isFunc(constructor.prototype.isPrototypeOf)) {
            return constructor.prototype.isPrototypeOf(object);
        }

        return false;
    });
}());
