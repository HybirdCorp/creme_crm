/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2021 Hybird
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

(function() {
    "use strict";

    window.console = window.console || {};

    function appendStatic(name, method) {
        /* istanbul ignore next */
        if (!window.console[name]) {
            window.console[name] = method;
        }
    }

    /* istanbul ignore next */
    function isIE() {
        var matches = navigator.appVersion.match(/MSIE ([\d.]+)/);

        if (matches === null) {
            return false;
        }

        if (arguments.length === 0) {
            return true;
        }

        for (var i = 0; i < arguments.length; ++i) {
            if (matches[1].indexOf('' + arguments[i]) !== -1) {
                return true;
            }
        }

        return false;
    }

    /* istanbul ignore next */
    appendStatic('log', function() {
        if (window.opera && window.opera.postError) {
            return window.opera.postError.apply(window.opera, arguments);
        }
    });

    appendStatic('warn', window.console.log);
    appendStatic('error', window.console.log);

    /* istanbul ignore next */
    if (isIE(9, 10)) {
        var methods = [ 'log', 'warn', 'error' ];
        methods.forEach(function(logger) {
            var _native = Function.prototype.bind
                    .call(console[logger], console);
            console[logger] = function() {
                return _native.apply(console, Array.copy(arguments).map(
                    function(item) {
                        if (typeof item === 'object' && JSON && JSON.stringify) {
                            return JSON.stringify(item, function(key, val) {
                                if (typeof val === 'function') {
                                    val = val.toString();
                                    return val.slice(0,
                                            val.indexOf(')') + 1);
                                } else {
                                    return val;
                                }
                            }) + ' ';
                        }

                        return item + ' ';
                    }));
            };
        });
    }
}());
