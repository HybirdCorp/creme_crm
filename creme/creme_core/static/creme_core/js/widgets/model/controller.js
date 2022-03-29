/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2022  Hybird

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

creme.model.CollectionController = creme.component.Component.sub({
    target: function(element) {
        if (element === undefined) {
            return this._target;
        }

        this._target = element !== null ? element : undefined;

        if (this.renderer()) {
            this.renderer().target(element);
        }

        return this;
    },

    redraw: function() {
        var renderer = this.renderer();
        var target = this.target();

        if (renderer && target) {
            renderer.redraw();
        }
    },

    _rendererModel: function() {
        return this._model;
    },

    renderer: function(renderer) {
        if (renderer === undefined) {
            return this._renderer;
        }

        this._renderer = renderer;

        if (this._renderer) {
            this._renderer.model(this._rendererModel());
            this._renderer.target(this.target());
        }

        return this;
    },

    model: function(model) {
        if (model === undefined) {
            return this._model;
        }

        this._model = model;

        if (this._renderer) {
            this._renderer.model(this._rendererModel());
        }

        return this;
    },

    fetch: function() {
        this.model().fetch();
        return this;
    }
});

creme.model.SelectionController = creme.component.Component.sub({
    _init_: function() {
        var events = this._events = new creme.component.EventHandler();
        this.selectionFilter(null);

        this._modelListeners = {
            'add remove': function(event, data) {
                              events.trigger('change', [], this);
                          },
            'update': function(event, data, start, end, previous, action) {
                          if (action !== 'select') {
                              events.trigger('change', [], this);
                          }
                      }
        };
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

    model: function(model) {
        if (model === undefined) {
            return this._model;
        }

        var previous = this._model;

        if (!Object.isNone(previous)) {
            previous.unbind(this._modelListeners);
        }

        if (!Object.isNone(model)) {
            model.bind(this._modelListeners);
            this._model = model;
        } else {
            this._model = undefined;
        }

        return this;
    },

    selectionFilter: function(filter) {
        if (filter === undefined) {
            return this._filter;
        }

        this._filter = Object.isFunc(filter) ? filter : null;
        return this;
    },

    selected: function() {
        var model = this.model();
        return model ? model.where(function(item) { return item.selected; }) : [];
    },

    selectables: function() {
        var model = this.model();
        var selectable = this._filter;

        if (model !== undefined) {
            return Object.isFunc(selectable) ? model.where(selectable) : model.all();
        }

        return [];
    },

    _inRange: function(indices, index) {
        if (indices.length === 0) {
            return false;
        }

        for (var i = 0; i < indices.length; ++i) {
            var range = indices[i];

            if (index >= range[0] && index <= range[1]) {
                return true;
            }
        }

        return false;
    },

    _cleanRange: function(range, min, max) {
        var start, end, swp;

        if (Array.isArray(range)) {
            start = parseInt(range[0]) || 0;
            end = parseInt(range[1]) || 0;
        } else {
            start = parseInt(range) || 0;
            end = start;
        }

        if (start > end) {
            swp = start;
            start = end;
            end = swp;
        }

        return [Math.min(Math.max(min, start), max),
                Math.max(min, Math.min(max, end))];
    },

    _compareRange: function(a, b) {
        return a[0] < b[0] ? -1 : (a[0] > b[0] ? 1 : 0);
    },

    _cleanIndices: function(indices, min, max) {
        if (Object.isFunc(indices)) {
            return this._cleanIndices(indices(this));
        }

        indices = Array.isArray(indices) ? indices : [indices];
        min = min || 0;
        max = max || this.model().length();

        var cleanRange = this._cleanRange;
        var cleaned = indices.map(function(range) {
                                      return cleanRange(range, min, max);
                                  })
                             .sort(this._compareRange);

        return cleaned;
    },

    _optimizeRanges: function(ranges) {
        var result = [];
        var current;

        ranges.sort(this._compareRange).forEach(function(range) {
            var start = range[0], end = range[1];

            if (current === undefined) {
                result.push(range);
                current = range;
            }

            var isStartIn = start >= current[0] && start <= current[1] + 1;

            if (isStartIn) {
                current[1] = Math.max(end, current[1]);
            } else {
                result.push(range);
                current = range;
            }
        });

        return result;
    },

    _updateSelection: function(indices, instate, outstate) {
        var model = this.model();
        var filter = this.selectionFilter();
        var inrange = this._inRange;
        var items = this.model().all();

        indices = this._cleanIndices(indices);

        var hasUpdates = false, outIndices = [];
        var next, previous, item, isInRange;

        for (var index = 0; index < items.length; ++index) {
            item = items[index];

            if (Object.isFunc(filter) && !filter(item, index)) {
                continue;
            }

            previous = (item.selected === true);
            isInRange = inrange(indices, index);

            if (isInRange) {
                next = instate(item, index);
            } else {
                next = outstate ? outstate(item, index) : previous;
            }

            if (next !== undefined && next !== previous) {
                item.selected = next;
                hasUpdates = true;

                if (!isInRange) {
                    outIndices.push([index, index]);
                }
            }
        }

        if (hasUpdates) {
            var updatedIndices = indices.concat(outIndices);

            updatedIndices.forEach(function(range) {
                var update_start = range[0];
                var update_end = range[1];

                model._fireUpdate(items.slice(update_start, update_end + 1),
                                  update_start, update_end,
                                  items.slice(update_start, update_end + 1),
                                  'select');
            });

            this._events.trigger('change', [], this);
        }

        return this;
    },

    toggle: function(indices, state) {
        return this._updateSelection(indices,
                                     function(item, index) {
                                         return state !== undefined ? (state === true) : !item.selected;
                                     });
    },

    select: function(indices, inclusive) {
        return this._updateSelection(indices,
                                     function(item, index) { return true; },
                                     inclusive ? undefined : function(item, index) { return false; });
    },

    unselect: function(indices) {
        return this._updateSelection(indices,
                                     function(item, index) { return false; });
    },

    toggleAll: function(state) {
        return this.toggle([[0, this.model().length() - 1]], state);
    },

    selectAll: function() {
        return this.toggleAll(true);
    },

    unselectAll: function() {
        return this.toggleAll(false);
    }
});
}(jQuery));
