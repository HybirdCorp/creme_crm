/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2025 Hybird
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

var _noop = function() {};

creme.component.EventHandler = creme.component.Component.sub({
    _init_: function() {
        this._listeners = {};
        this._error = _noop;
    },

    on: function(key, listener, decorator) {
        return this.bind(key, listener, decorator);
    },

    off: function(key, listener) {
        return this.unbind(key, listener);
    },

    one: function(key, listener, decorator) {
        var self = this;

        if (Object.isFunc(decorator)) {
            return this.bind(key, listener, function(key, listener, args) {
                self.unbind(key, listener);
                return decorator.apply(this, [key, listener, args]);
            });
        }

        return this.bind(key, listener, function(key, listener, args) {
            self.unbind(key, listener);
            return listener.apply(this, args);
        });
    },

    bind: function(key, listener, decorator) {
        var self = this;

        if (Array.isArray(key)) {
            key.forEach(function(key) {
                self.bind(key, listener, decorator);
            });
            return this;
        }

        if (typeof key === 'object') {
            for (var k in key) {
                this.bind(k, key[k], decorator);
            }
            return this;
        }

        if (typeof key === 'string' && key.indexOf(' ') !== -1) {
            return this.bind(key.split(' '), listener, decorator);
        }

        if (Array.isArray(listener)) {
            listener.forEach(function(listener) {
                self.bind(key, listener, decorator);
            });
            return this;
        }

        if (Object.isFunc(listener) === false) {
            throw new Error('unable to bind event "' + key + '", listener is not a function');
        }

        var listeners = this.listeners(key);

        listener.__eventuuid__ = listener.__eventuuid__ || _.uniqueId();

        if (Object.isFunc(decorator)) {
            var proxy = (function(key, listener, decorator) {
                return function() {
                    return decorator.apply(this, [key, listener, Array.from(arguments)]);
                };
            })(key, listener, decorator);

            proxy.__eventuuid__ = listener.__eventuuid__;
            listeners.push(proxy);
        } else {
            listeners.push(listener);
        }

        this._listeners[key] = listeners;
        return this;
    },

    unbind: function(key, listener) {
        var self = this;

        if (Array.isArray(key)) {
            key.forEach(function(key) {
                self.unbind(key, listener);
            });
            return this;
        }

        if (typeof key === 'object') {
            for (var k in key) {
                this.unbind(k, key[k]);
            }
            return this;
        }

        if (typeof key === 'string' && key.indexOf(' ') !== -1) {
            return this.unbind(key.split(' '), listener);
        }

        var listeners = this.listeners(key);

        if (listener === undefined) {
            listeners.splice(0, listeners.length);
            return this;
        }

        if (Array.isArray(listener)) {
            listener.forEach(function(l) {
                self._remove(listeners, l);
            });
        } else {
            this._remove(listeners, listener);
        }

        return this;
    },

    _remove: function(listeners, listener) {
        var index = 0;

        while (index < listeners.length) {
            var item = listeners[index];

            if (item && item.__eventuuid__ !== undefined && (item.__eventuuid__ === listener.__eventuuid__)) {
                listeners.splice(index, 1);
            } else {
                ++index;
            }
        }
    },

    error: function(error) {
        if (error === undefined) {
            return this._error;
        }

        if (error === null) {
            this._error = _noop;
            return this;
        }

        if (Object.isFunc(error) === false) {
            throw new Error('event error handler is not a function');
        }

        this._error = error;
        return this;
    },

    listeners: function(key) {
        return this._listeners[key] || [];
    },

    trigger: function(key, data, source) {
        source = source || this;
        data = Array.isArray(data) ? data : (data !== undefined ? [data] : []);
        var args = [key].concat(data);
        var error = this._error.bind(source);

        Array.from(this.listeners(key)).forEach(function(listener) {
            try {
                listener.apply(source, args);
            } catch (e) {
                console.error(key, data, listener, e, source);
                error(e, key, data, listener);
            }
        });
    }
});
}(jQuery));
