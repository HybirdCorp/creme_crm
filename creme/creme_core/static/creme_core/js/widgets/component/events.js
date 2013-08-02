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

creme.component.EventHandler = creme.component.Component.sub({
    _init_: function() {
        this._listeners = {};
    },

    bind: function(key, listener)
    {
        var self = this;

        if (Array.isArray(key)) {
            key.forEach(function(key) {self.bind(key, listener);});
            return this;
        }

        var listeners = this.listeners(key);

        if (Array.isArray(listener)) {
            listener.forEach(function(listener) {listeners.push(listener)});
        } else {
            listeners.push(listener);
        }

        this._listeners[key] = listeners;
        return this;
    },

    unbind: function(key, listener)
    {
        var self = this;

        if (Array.isArray(key)) {
            key.forEach(function(key) {self.unbind(key, listener);});
            return this;
        }

        var listeners = this.listeners(key);

        if (listener === undefined) {
            listeners.splice(0, listeners.length);
            return this;
        }

        var remove = function(listener) {
            var index = 0;

            while((index = listeners.indexOf(listener)) !== -1) {
                listeners.splice(index, 1)
            }
        };

        if (Array.isArray(listener)) {
            listener.forEach(remove);
        } else {
            remove(listener);
        }

        return this;
    },

    listeners: function(key) {
        return this._listeners[key] || [];
    },

    trigger: function(key, data, source)
    {
        var source = source || this;
        var data = Array.isArray(data) ? data : (data !== undefined ? [data] : []);
        var args = [key].concat(data);

        this.listeners(key).forEach(function(listener) {
            try {
                listener.apply(source, args);
            } catch(e) {
            }
        });
    }
});
