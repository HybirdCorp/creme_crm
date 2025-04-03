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

creme.model = creme.model || {};

creme.model.Collection = creme.component.Component.sub({
    _init_: function() {
        this._events = new creme.component.EventHandler();
    },

    bind: function(event, listener, decorator) {
        this._events.bind(event, listener, decorator);
        return this;
    },

    unbind: function(event, listener) {
        this._events.unbind(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
    },

    _fireAdd: function(data, start, end, action) {
        this._events.trigger('add', [data, start, end, action], this);
    },

    _fireRemove: function(data, start, end, action) {
        this._events.trigger('remove', [data, start, end, action], this);
    },

    _fireUpdate: function(data, start, end, previous, action) {
        this._events.trigger('update', [data, start, end, previous, action], this);
    },

    length: function() {
        return this.all().length;
    },

    get: function(index) {
        return this.all()[index];
    },

    each: function(cb) {
        return this.all().forEach(cb);
    },

    map: function(cb) {
        return this.all().map(cb);
    },

    where: function(cb) {
        return this.all().filter(cb);
    },

    slice: function(start, end) {
        return this.all().slice(start, end);
    },

    first: function() {
        return this.length() > 0 ? this.get(0) : undefined;
    },

    last: function() {
        return this.length() > 0 ? this.get(this.length() - 1) : undefined;
    },

    all: function() {
        return [];
    }
});

creme.model.Delegate = creme.model.Collection.sub({
    _init_: function(delegate, listeners) {
        this._super_(creme.model.Collection, '_init_');

        this._delegateListener = $.extend({
            update: this._onUpdate.bind(this),
            add: this._onAdd.bind(this),
            remove: this._onRemove.bind(this)
        }, listeners || {});

        this.delegate(delegate);
    },

    delegate: function(delegate) {
        if (delegate === undefined) {
            return this._delegate;
        }

        var previous = this._delegate;

        if (previous !== undefined) {
            previous.unbind(this._delegateListener);
        }

        if (!Object.isNone(delegate)) {
            delegate.bind(this._delegateListener);
        }

        this._delegate = delegate;
        return this;
    },

    all: function() {
        return this._delegate ? this._delegate.all() : [];
    },

    _onUpdate: function(event, data, start, end, previous, action) {
        this._fireUpdate(data, start, end, previous, action);
    },

    _onAdd: function(event, data, start, end, action) {
        this._fireAdd(data, start, end, action);
    },

    _onRemove: function(event, data, start, end, action) {
        this._fireRemove(data, start, end, action);
    }
});

creme.model.Filter = creme.model.Delegate.sub({
    _init_: function(delegate, filter) {
        var listeners = {
            reset: this._onReset.bind(this)
        };

        this._setFilter(filter);
        this._super_(creme.model.Delegate, '_init_', delegate, listeners);
    },

    all: function() {
        return this._data;
    },

    fetch: function(start, end) {
        var data = this._filterData();
        this._super_(creme.model.Array, 'reset', data);
        return this;
    },

    _filterData: function() {
        var delegate = this._delegate;
        var filter = this._filter;

        if (!delegate) {
            return [];
        }

        return Object.isFunc(filter) ? delegate.where(filter) : delegate.all().slice();
    },

    _setFilter: function(filter) {
        if (Object.isNone(filter)) {
            this._filter = null;
        } else if (Object.isFunc(filter)) {
            this._filter = filter;
        } else if (Object.isFunc(filter.callable)) {
            this._filter = filter.callable();
        } else if (Object.isType(filter, 'string')) {
            this._filter = creme.utils.lambda(filter, 'item', null);
        }
    },

    filter: function(filter) {
        if (filter === undefined) {
            return this._filter;
        }

        this._setFilter(filter);
        this.fetch();

        return this;
    },

    delegate: function(delegate) {
        var previous = this._delegate;
        var ret = this._super_(creme.model.Delegate, 'delegate', delegate);

        if (previous !== this._delegate) {
            this.fetch();
        }

        return ret;
    },

    _onUpdate: function(event, data, start, end, previous, action) {
        if (action !== 'reset') {
            this.fetch();
        }
    },

    _onAdd: function(event, data, start, end, previous, action) {
        if (action !== 'reset') {
            this.fetch();
        }
    },

    _onRemove: function(event, data, start, end, previous, action) {
        if (action !== 'reset') {
            this.fetch();
        }
    },

    _onReset: function(event) {
        this.fetch();
    }
});
}(jQuery));
