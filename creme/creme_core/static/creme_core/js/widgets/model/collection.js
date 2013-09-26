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
        return this.all().slice(start, end)
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


creme.model.Array = creme.model.Collection.sub({
    _init_: function(data, comparator)
    {
        this._super_(creme.model.Collection, '_init_');
        this._data = !Object.isEmpty(data) ? (Array.isArray(data) ? data : [data]) : [];
        this.comparator(comparator);
    },

    length: function() {
        return this._data.length;
    },

    get: function(index) {
        return this._data[index];
    },

    set: function(data, index)
    {
        if (index < 0 || index > this._data.length) {
            throw new Error('index out of bound');
        }

        var previous = this._data[index];

        this._data[index] = data;
        this._fireUpdate([data], index, index, [previous], 'set');
        return this;
    },

    reset: function(data)
    {
        var previous = this._data;
        var previous_length = previous ? previous.length : 0;

        this._data = !Object.isEmpty(data) ? (Array.isArray(data) ? data : [data]) : [];

        var next_length = this._data.length;

        if (previous_length > 0)
        {
            if (next_length > 0)
            {
                var update_start = 0;
                var update_end = Math.max(0, Math.min(previous.length - 1, this._data.length - 1));

                this._fireUpdate(this._data.slice(update_start, update_end + 1),
                                 update_start, update_end, 
                                 previous.slice(update_start, update_end + 1),
                                 'reset');
            }

            if (previous_length > next_length)
            {
                var remove_start = next_length;
                var remove_end = previous_length - 1;

                this._fireRemove(previous.slice(remove_start, remove_end + 1), remove_start, remove_end, 'reset');
            }
        }

        if (next_length > 0 && next_length > previous_length)
        {
            var add_start = previous_length;
            var add_end = next_length - 1;

            this._fireAdd(this._data.slice(add_start, add_end + 1), add_start, add_end, 'reset');
        }

        this._events.trigger('reset', [], this);
        return this;
    },

    insert: function(data, index)
    {
        var self = this;
        var data = Array.isArray(data) ? data : [data];
        var index = index || 0;

        var start = index;
        var end = start + (data.length - 1);

        if (data.length === 0)
            return this;

        if (index < 0 || index > this._data.length) {
            throw new Error('index out of bound');
        }

        if (index === this._data.length) {
            this._data = this._data.concat(data);
        } else if (index === 0) {
            this._data = data.concat(this._data);
        } else {
            this._data = this._data.slice(0, index).concat(data, this._data.slice(index));
        }

        this._fireAdd(data, start, end, 'insert');
        return this;
    },

    append: function(data) {
        return this.insert(data, this._data.length);
    },

    prepend: function(data) {
        return this.insert(data);
    },

    pop: function()
    {
        if (this._data.length === 0)
            return;

        var index = this._data.length - 1;
        var item = this._data.pop();

        this._fireRemove([item], index, index, 'remove');
        return item;
    },

    removeAt: function(index)
    {
        if (index < 0 || index > this._data.length) {
            throw new Error('index out of bound');
        }

        var item = this._data.splice(index, 1);
        this._fireRemove(item, index, index, 'remove');
        return item[0];
    },

    remove: function(value)
    {
        var self = this;
        var value = Array.isArray(value) ? value : [value];
        var data = this._data;
        var removed = [];
        var index = -1;

        value.forEach(function(item) {
            var index = self.indexOf(item);

            if (index != -1) {
                removed.push(self.removeAt(index));
            }
        });

        return removed;
    },

    indexOf: function(value)
    {
        var comparator = this._comparator;
        var data = this._data;

        if (Object.isFunc(comparator) === false)
            return data.indexOf(value);

        for(var index = 0; index < data.length; ++index)
        {
            if (comparator(data[index], value) === 0)
                return index;
        }

        return -1;
    },

    clear: function()
    {
        var data = this._data;
        this._data = [];
        this._fireRemove(data, 0, data.length - 1, 'clear');

        return data;
    },

    first: function() {
        return this._data ? this._data[0] : undefined;
    },

    last: function() {
        return this._data ? this._data[this._data.length - 1] : undefined;
    },

    each: function(cb)
    {
        this._data.forEach(cb);
        return this;
    },

    map: function(cb) {
        return this._data.map(cb);
    },

    where: function(cb) {
        return this._data.filter(cb);
    },

    slice: function(start, end) {
        return this._data.slice(start, end)
    },

    all: function() {
        return this._data;
    },

    comparator: function(comparator) {
        return Object.property(this, '_comparator', comparator);
    },

    sort: function(comparator)
    {
        var data = this._data;
        var previous = Array.copy(data);
        var comparator = comparator || this._comparator;

        data.sort(comparator);

        this._fireUpdate(data, 0, data.length - 1, previous, 'sort');
        this._events.trigger('sort', [], this);

        return this;
    },

    reverse: function()
    {
        var data = this._data;
        var previous = Array.copy(data);

        data.reverse();

        this._fireUpdate(data, 0, data.length - 1, previous, 'reverse');
        this._events.trigger('reverse', [], this);

        return this;
    }
});

creme.model.Delegate = creme.model.Collection.sub({
    _init_: function(delegate, listeners)
    {
        this._super_(creme.model.Collection, '_init_');

        this._delegateListener = $.extend({
            update: $.proxy(this._onUpdate, this),
            add: $.proxy(this._onAdd, this),
            remove: $.proxy(this._onRemove, this)
        }, listeners || {});

        this.delegate(delegate);
    },

    delegate: function(delegate)
    {
        if (delegate === undefined)
            return this._delegate;

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
    _init_: function(delegate, filter)
    {
        var listeners = {
           reset: $.proxy(this._onReset, this)
        };

        this._filter = Object.isFunc(filter) ? filter : null;
        this._super_(creme.model.Delegate, '_init_', delegate, listeners);
    },

    all: function() {
        return this._data;
    },

    fetch: function()
    {
        var data = [];

        if (this._delegate)
            data = Object.isFunc(this._filter) ? this._delegate.where(this._filter) : this._delegate.all();

        this._super_(creme.model.Array, 'reset', data);
    },

    filter: function(filter)
    {
        if (filter === undefined)
            return this._filter;

        this._filter = Object.isFunc(filter) ? filter : null;
        this.fetch();
    },

    delegate: function(delegate)
    {
        var previous = this._delegate;
        var ret = this._super_(creme.model.Delegate, 'delegate', delegate);

        if (previous != this._delegate) {
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
