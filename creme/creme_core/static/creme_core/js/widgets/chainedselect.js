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

creme.widget.ChainedSelect = creme.widget.declare('ui-creme-chainedselect', {
    options: {
        backend: undefined,
        json: true
    },

    _create: function(element, options, cb, sync) {
        var self = this;

        this._backend = options.backend || creme.ajax.defaultCacheBackend();
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._context = {};

        this.selectors(element).each(function() {
            $(this).creme().create({backend: self._backend, disabled: !self._enabled}, undefined, true);
        });

        this._dependency_change = function(e) {
            var selector_name = $(this).parent().attr('chained-name');
            var previous = self._context[selector_name];
            var next = $(this).creme().widget().cleanedval();

            // console.log(selector_name, '=> previous:', previous, 'next:', next, 'val:', $(this).val())

            if (previous !== next) {
                // console.log('chainedselect._dependency_change > element:' + previous + ' has changed. val:' + next);
                self._reloadDependencies(element, selector_name, next);
                self._update(element);
            }
        };

        this._dependency_change_multiple = function(e, data) {
            e.stopPropagation();

            var name = $(this).parent().attr('chained-name');
            var value = self._selectorValues(element);

            data = Array.isArray(data) ? data : [data];

            var chained_data = data.map(function(item) {
                value[name] = item;
                return Object.assign({}, value);
            });

            element.trigger('change-multiple', [chained_data]);
        };

        $('img.reset', element).on('click', function() {
            if (self._enabled) {
                self.reset(element);
            }
        });

        var data = this.cleanedval(element);

        // reload all selectors from actual values in order to initialize them all
        var values = this._selectorValues(element);

        this._reloadSelectors(element, values);
        this.selectors(element).on('change', self._dependency_change);
        this.selectors(element).on('change-multiple', self._dependency_change_multiple);

        // if empty data, get values from selector and try to force it in widget
        if (Object.isEmpty(data)) {
            this.val(element, values);
        } else {
            this._updateSelectors(element, data);
            this._update(element);
        }

        element.addClass('widget-ready');
        creme.object.invoke(cb, element);
    },

    _destroy: function(element) {
        this.selectors(element).each(function() {
            $(this).creme().destroy();
        });
    },

    _selectorValues: function(element) {
        var data = {};

        this.selectors(element).each(function() {
            var selector = $(this);

            var value = selector.creme().widget().cleanedval();
            var name = selector.parent().attr('chained-name');

            // console.log('chainedselect._selectorValues > name="' + name + '", value="' + value + '", type=' + (typeof value), ' val=', selector.val());
            data[name] = value;
        });

        return data;
    },

    _update: function(element) {
        this._context = this._selectorValues(element);
        creme.widget.input(element).val(JSON.stringify(this._context));
    },

    _updateSelector: function(selector, data) {
        var name = selector.element.parent().attr('chained-name');
        var value = typeof data === 'object' ? data[name] : undefined;
        selector.val(value);
    },

    _updateSelectors: function(element, data) {
        var self = this;

        this.selectors(element).each(function() {
            self._updateSelector($(this).creme().widget(), data);
        });
    },

    _reloadSelector: function(target, name, data) {
        var ready = target.is('.widget-ready');
        var widget = target.creme().widget();

        if (ready && (widget.dependencies() || []).indexOf(name) !== -1) {
            widget.reload(data, undefined, undefined, true);
        }
    },

    _reloadSelectors: function(element, data) {
        for (var name in data) {
            this._reloadDependencies(element, name, data[name]);
        }
    },

    _reloadDependencies: function(element, name, value) {
        var self = this;
        var data = this._context;

        data[name] = value;

        // console.log('chainedselect._reloadDependencies >', name, ':', data[name]);

        this.selectors(element).each(function() {
            self._reloadSelector($(this), name, data);
        });

        // console.log('chainedselect._reloadDependencies >', data, '> end');
    },

    selector: function(element, name) {
        return $(
            '[chained-name="' + name + '"].ui-creme-chainedselect-item:last > .ui-creme-widget',
            element
        ).filter(function() {
            return $(this).parents('.ui-creme-chainedselect').first().is(element);
        });
    },

    selectors: function(element) {
        return $(
            '.ui-creme-chainedselect-item > .ui-creme-widget', element
        ).filter(function() {
            return $(this).parents('.ui-creme-chainedselect').first().is(element);
        });
    },

    reset: function(element) {
        this.selectors(element).each(function() {
            $(this).creme().widget().reset();
        });
    },

    update: function(element, data) {
        data = creme.widget.cleanval(data, {});

        var added = data.added || [];
        var removed = data.removed || [];
        var notempty = function(item) {
            return Object.isEmpty(item) === false;
        };

        this.selectors(element).each(function() {
            var selector = $(this);
            var name = selector.parent().attr('chained-name');
            var widget = selector.creme().widget();

            if (Object.isFunc(widget.update)) {
                var getter = function(item) { return item[name]; };
                var selector_added = added.map(getter).filter(notempty);
                var selector_removed = removed.map(getter).filter(notempty);

                widget.update({
                    added: selector_added,
                    removed: selector_removed
                });
            }
        });

        return this.val(element, data.value);
    },

    context: function(element) {
        return Object.assign({}, this._context);
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.widget.input(element).val();
        }

        this._updateSelectors(element, creme.widget.cleanval(value, {}));
        this._update(element);
        element.trigger('change');
    }
});

}(jQuery));
