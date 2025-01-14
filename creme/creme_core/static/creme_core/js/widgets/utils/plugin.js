/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2020-2025 Hybird
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

    Assert.not(Object.isEmpty(name), 'Missing JQuery plugin name.');

    Assert.that(Object.isFunc(constructor),
                'JQuery plugin "${name}" constructor is not a function.',
                {name: name});

    Assert.that(Object.isFunc(destructor),
                'JQuery plugin "${name}" destructor is not a function.',
                {name: name});

    Assert.that(Object.isNone($.fn[name]),
                'JQuery plugin "${name}" already exist.',
                {name: name});

    ['prop', 'props', 'destroy', 'instance'].forEach(function(builtin) {
        Assert.notIn(
            builtin, methods,
            'Method "${value}" is a builtin of JQuery plugin "${name}".', {
                name: name
            });
    });

    $.fn[name] = function(methodname, key, value) {
        var args = Array.from(arguments);

        var resultList = this.get().map(function(element) {
            var instanceKey = '-' + name;
            var instance = $.data(element, instanceKey);

            /* new instance of plugin */
            if (Object.isString(methodname) === false) {
                if (Object.isNone(instance)) {
                    instance = constructor.apply(element, args);

                    Assert.not(Object.isNone(instance),
                               'Jquery plugin "${name}" constructor has returned nothing.',
                               {name: name});

                    $.data(element, instanceKey, instance);
                } else {
                    Assert.not(args.length > 0,
                               'Jquery plugin "${name}" is already initialized.',
                               {name: name});
                }

                return instance;
            }

            var result;

            if (Object.isNone(instance)) {
                return;
            }

            if (methodname === 'prop') {
                Assert.in(key, properties,
                          'No such property "${value}" in jQuery plugin "${name}"',
                          {name: name});

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
                $(element).removeData(instanceKey);
            } else if (methodname === 'instance') {
                return instance;
            } else {
                Assert.in(methodname, methods,
                          'No such method "${value}" in jQuery plugin "${name}"',
                          {name: name});

                var method = instance[methodname];
                Assert.that(Object.isFunc(method),
                            'Attribute "${method}" is not a function in jQuery plugin "${name}"',
                            {method: methodname, name: name});

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
