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

creme.model.CollectionController = creme.component.Component.sub({
    target: function(element)
    {
        if (element === undefined)
            return this._target;

        this._target = element !== null ? element : undefined;
        
        if (this.renderer()) {
            this.renderer().target(element);
        }

        return this;
    },

    redraw: function()
    {
        var renderer = this.renderer();
        var target = this.target();
        
        if (renderer && target)
            renderer.redraw();
    },

    _rendererModel: function() {
        return this._model;
    },

    renderer: function(renderer)
    {
        if (renderer === undefined)
            return this._renderer;

        this._renderer = renderer;

        if (this._renderer)
        {
            this._renderer.model(this._rendererModel());
            this._renderer.target(this.target());
        }

        return this;
    },

    model: function(model)
    {
        if (model === undefined)
            return this._model;

        this._model = model;

        if (this._renderer) {
            this._renderer.model(this._rendererModel());
        }

        return this;
    },

    fetch: function()
    {
        this.model().fetch();
        return this;
    },
});


creme.model.SelectionController = creme.component.Component.sub({
    _init_: function() {
        this._events = new creme.component.EventHandler();
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
    },

    model: function(model)
    {
        if (model === undefined)
            return this._model;

        this._model = model;

        if (model)
        {
            model.bind('update add remove', function() {
                this._events.trigger('change', [], this);
            });
        }

        return this;
    },

    isItemSelectable: function(item, index) {
        return true;
    },

    selected: function()
    {
        var model = this.model();
        return model ? model.where(function(item) {return item.selected;}) : [];
    },

    select: function(selections, key)
    {
        var model = this.model();

        if (model === undefined) {
            return this;
        }

        var selections = selections.slice();
        var selectable = this.isItemSelectable;
        var key = key;

        model.all().forEach(function(item, index) {
            var selectionIndex = selections ? selections.indexOf(key ? key(item, index) : index) : -1;
            var isSelected = selectionIndex !== -1;

            if (isSelected)
                selections.splice(selectionIndex, 1);

            if (Object.isFunc(selectable) && selectable(item, index))
                item.selected = isSelected;
        });

        model.reset(model.all());
        this._events.trigger('change', [], this);

        return this;
    },

    toggle: function(index, state)
    {
        var item = this.model().get(index);

        if (!this.isItemSelectable(item, index))
            return this;

        item.selected = state !== undefined ? (state === true) : !item.selected;

        this.model().set(item, index);
        this._events.trigger('change', [], this);
        return this;
    },

    toggleAll: function(state)
    {
        var selectable = this.isItemSelectable;

        var items = this.model().all().map(function(item) {
            if (selectable(item)) {
                item.selected = (state !== undefined) ? (state === true) : !item.selected;
            }

            return item;
        });

        this.model().reset(items);
        this._events.trigger('change', [], this);
        return this;
    }
});
