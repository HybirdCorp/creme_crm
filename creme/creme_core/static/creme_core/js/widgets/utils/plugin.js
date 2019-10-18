/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2019 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

creme.utils = creme.utils || {};

var _noop = function() {};

var _assert = function(test, message) {
    test = Boolean(Object.isFunc(test) ? test() : test);

    if (test === false) {
        throw new Error(message);
    }
};

var _assertNot = function(test, message) {
    test = Boolean(Object.isFunc(test) ? test() : test);

    if (test === true) {
        throw new Error(message);
    }
};

var _getter = function(instance, key) {
    var prop = instance[key];
    return Object.isFunc(prop) ? prop.apply(instance) : prop;
};

var _setter = function(instance, key, value) {
    var prop = instance[key];

    if (Object.isFunc(prop)) {
        prop.apply(instance, [value]);
    } else {
        instance[key] = value;
    }

    return instance;
};

creme.utils.newJQueryPlugin = function(options) {
    options = options || {};

    var methods = options.methods || [];
    var properties = options.properties || [];
    var name = options.name;
    var constructor = options.create;
    var destructor = options.destroy || _noop;

    _assertNot(Object.isEmpty(name),
               'Missing JQuery plugin name.');

    _assert(Object.isFunc(constructor),
            'JQuery plugin "${name}" constructor is not a function.'.template({name: name}));

    _assert(Object.isFunc(destructor),
            'JQuery plugin "${name}" destructor is not a function.'.template({name: name}));

    _assert(Object.isNone($.fn[name]),
            'JQuery plugin "${name}" already exist.'.template({name: name}));

    ['prop', 'props', 'destroy'].forEach(function(builtin) {
        _assert(methods.indexOf(builtin) === -1, (
                'Method "${builtin}" is a builtin of JQuery plugin "${name}".').template({
                    name: name, builtin: builtin
                }));
    });

    $.fn[name] = function(methodname, key, value) {
        var args = Array.copy(arguments);

        var resultList = this.get().map(function(element) {
            var instance = $.data(element, name);

            /* new instance of plugin */
            if (Object.isString(methodname) === false) {
                if (Object.isNone(instance)) {
                    instance = constructor.apply(element, args);

                    _assertNot(Object.isNone(instance),
                               'Jquery plugin "${name}" constructor has returned nothing.'.template({name: name}));

                    $.data(element, name, instance);
                } else {
                    _assertNot(args.length > 0,
                               'Jquery plugin "${name}" is already initialized.'.template({name: name}));
                }

                return instance;
            }

            var result;

            if (Object.isNone(instance)) {
                return;
            }

            if (methodname === 'prop') {
                _assert(properties.indexOf(key) !== -1,
                        'No such property "${key}" in jQuery plugin "${name}"'.template({key: key, name: name}));

                if (args.length > 2) {
                    result = _setter(instance, key, value);
                } else {
                    result = _getter(instance, key);
                }
            } else if (methodname === 'props') {
                result = {};

                properties.forEach(function(prop) {
                    result[prop] = _getter(instance, prop);
                });
            } else if (methodname === 'destroy') {
                destructor.apply(element, [instance]);
                $(element).removeData(name);
            } else {
                _assert(methods.indexOf(methodname) !== -1,
                        'No such method "${method}" in jQuery plugin "${name}"'.template({method: methodname, name: name}));

                var method = instance[methodname];
                _assert(Object.isFunc(method),
                        'Attribute "${method}" is not a function in jQuery plugin "${name}"'.template({method: methodname, name: name}));

                result = method.apply(instance, args.slice(1));
            }

            return result;
        }).filter(function(item) {
            return item !== undefined;
        });

        if (this.length > 1) {
            return resultList;
        } else {
            return resultList.length === 1 ? resultList[0] : undefined;
        }
    };
};

}(jQuery));
