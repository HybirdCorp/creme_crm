/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2009-2013  Hybird

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
    function appendStatic(name, method)
    {
        if(!Object[name])
            Object[name] = method;
    };

    function append(name, method)
    {
        if(!Object.prototype[name])
            Object.prototype[name] = method;
    };

    appendStatic('property', function(obj, key, value) {
        if (value === undefined)
            return obj[key];

        obj[key] = value;
        return obj;
    });

    appendStatic('keys', function(obj, all) {
        var keys = [];
        var key;

        for (key in obj) {
            if (all || obj.hasOwnProperty(key)) {
                keys.push(key);
            }
        }

        return keys;
    });

    appendStatic('values', function(obj, all) {
        values = [];

        for(key in obj) {
            if (all || obj.hasOwnProperty(key)) {
                values.push(obj[key]);
            }
        }

        return values;
    });

    appendStatic('entries', function(obj, all) {
        entries = [];

        for(key in obj) {
            if (all || obj.hasOwnProperty(key)) {
                entries.push([key, obj[key]]);
            }
        }

        return entries;
    });

    appendStatic('isNone', function(obj) {
        return obj === undefined || obj === null;
    });

    appendStatic('isEmpty', function(obj) {
        if (Object.isNone(obj) || obj.length === 0)
            return true

        if (typeof obj === 'number')
            return false;

        for(var name in obj) {
            return false;
        }

        return true;
    });

    appendStatic('isType', function(obj, type) {
        return (typeof obj === type);
    });

    appendStatic('isFunc', function(obj) {
        return (typeof obj === 'function');
    });

    appendStatic('proxy', function(delegate, context, options) {
        if (Object.isNone(delegate))
            return;

        var options = options || {};

        var context = context || delegate;
        var proxy = {__context__: context || {}};
        var filter = Object.isFunc(options.filter) ? options.filter : function() {return true}
        var parameters = Object.isFunc(options.arguments) ? function(args) {return options.arguments(Array.copy(args));} : Array.copy;

        for(key in delegate)
        {
            var value = delegate[key];

            if (!Object.isFunc(value) || filter(key, value) === false)
                continue;

            // use a function to 'keep' the current loop step context
            (function(proxy, fn, key) {
                proxy[key] = function() {
                    return fn.apply(this.__context__, parameters(arguments));
                };
            })(proxy, value, key);
        }

        return proxy;
    });

    appendStatic('getPrototypeOf', function(object) {
        if (typeof "".__proto__ === 'object')
            return object.__proto__;

        if (Object.isNone(object) || object === Object.prototype)
            return null;

        return Object.isNone(object.constructor) ? null : object.constructor.prototype;
    });
})();