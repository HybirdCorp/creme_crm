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

creme.model.Renderer = creme.component.Component.sub({
    _init_: function(target, model, listeners)
    {
        var self = this;

        this._modelListener = $.extend({
            update: $.proxy(this._onUpdate, this),
            add: $.proxy(this._onAdd, this),
            remove: $.proxy(this._onRemove, this)
        }, listeners || {});

        this.target(target);
        this.model(model);
    },

    target: function(target) {
        return Object.property(this, '_target', target);
    },

    model: function(model)
    {
        if (model === undefined)
            return this._model;

        var previous = this._model;

        if (previous !== undefined) {
            previous.unbind(this._modelListener);
        }

        if (!Object.isNone(model)) {
            model.bind(this._modelListener);
        }

        this._model = model;
        return this;
    },

    redraw: function()
    {
        this._target.html('');

        if (this._model && this._model.length() > 0) {
            this.added(model._data, 0, model._data.length - 1);
        }
    }
});


creme.model.ListRenderer = creme.model.Renderer.sub({
    items: function(target) {
        return target ? $('li', target) : $([]);
    },

    createItem: function(target, before, data, index) {
        return $('<li>').html(data);
    },

    insertItem: function(target, before, data, index)
    {
        var item = this.createItem(target, before, data, index)
        
        if (before && before.length) {
            before.before(item);
        } else {
            target.append(item);
        }
    },

    updateItem: function(target, item, data, previous, index) {
        item.html(data);
        return item;
    },

    removeItem: function(target, item, data, index) {
        item.remove();
    },

    redraw: function()
    {
        var target = this._target;
        var self = this;
        var model = this.model();

        this.items(target).each(function(index) {
            self.removeItem(target, $(this), model !== undefined ? model.get(index) : undefined, index)
        });

        if (model === undefined)
            return this;

        model.all().forEach(function(data, index) {
            self.insertItem(target, $([]), data, index);
        });

        return this;
    },

    _onUpdate: function(event, data, start, end, previous, action)
    {
        var self = this;
        var target = this._target;

        this.items(target).slice(start, end + 1).each(function(index) {
            self.updateItem(target, $(this), data[index], previous[index], start + index);
        });
    },

    _onAdd: function(event, data, start, end, action)
    {
        var target = this._target;
        var self = this;
        var before = this.items(target).slice(start, start + 1);

        data.forEach(function(entry, index) {
            self.insertItem(target, before, entry, start + index);
        });
    },

    _onRemove: function(event, data, start, end, action)
    {
        var target = this._target;
        var self = this;

        this.items(target).slice(start, end + 1).each(function(index) {
            self.removeItem(target, $(this), data[index], start + index);
        });
    }
});
