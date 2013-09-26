/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.widget.PolymorphicSelect = creme.widget.declare('ui-creme-polymorphicselect', {
    options: {
        key: null,
        dependencies: ''
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;

        this._context = {};
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);
        this._selectorKey = new creme.utils.Template(options.key);
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        this._selector_onchange_cb = function() {
            element.change();
        };

        this._init_models(element);

        this.reload(element, {}, cb, cb);
        element.addClass('widget-ready');
    },

    _init_models: function(element)
    {
        var models = this._models = [];

        $('> script[selector-key]', element).each(function() {
            var pattern = new RegExp($(this).attr('selector-key').replace('.', '\.').replace('*', '.*'));
            var content = new creme.utils.Template($(this).html());

            //console.log('pattern:', pattern, 'content:', content);
            models.push({pattern:pattern, content:content});
        });
    },

    _updateSelector: function(element, selector, value, cb, sync)
    {
        var self = this;

        if (Object.isNone(selector)) {
            creme.object.invoke(cb, element);
            return this;
        }

        selector.val(value);
    },

    _removeSelector: function(element)
    {
        if (this._selector !== undefined)
        {
            this._selector.element.unbind('change paste', this._selector_onchange_cb);
            this._selector.element.remove();
            this._selector.destroy();
            this._selector = undefined;
            this._selectorModel = undefined;
        }

        if (this._target) {
            this._target.remove();
            this._target = undefined;
        }
    },

    _createSelector: function(element, model, value, cb, error_cb, sync)
    {
        var self = this;

        this._target = $('<span>').addClass('delegate').html(model).appendTo(element);
        var selector = $('> .delegate > .ui-creme-widget:first', element);

        if (selector.length !== 1)
            return;

        creme.widget.create(selector, {}, function(delegate) {
            creme.object.invoke(cb, element);
            delegate.bind('change paste', self._selector_onchange_cb);
            element.change();
        }, sync);

        this._selector = selector.creme().widget();
        this._selectorModel = model;
    },

    toggleSelector: function(element, previous_key, cb, error_cb, sync)
    {
        var value = this.val(element);
        var previous = this._selector;
        var previous_model = this._selectorModel;

        var key = this.selectorKey(element);
        var model = this.selectorModel(element, key);

        if (Object.isNone(model)) {
            this._removeSelector(element);
            return;
        }

//        console.log('key:', '"' + key + '"', 'value:', value, 'context:', this._selectorKey.parameters,
//                    'deps:', this.dependencies(element),
//                    'deps:', previous !== undefined ? previous.dependencies() : undefined,
//                    'same:', previous_model !== undefined && previous_model === model);

        // already active selector, set value and get out !
        if (previous_model !== undefined && previous_model === model) {
            return this._updateSelector(element, previous, value, cb, sync);
        }

        this._removeSelector(element);
        this._createSelector(element, model, null, cb, error_cb, sync);
    },

    selectorKey: function(element) {
        return (this._selectorKey && this._selectorKey.iscomplete()) ? this._selectorKey.render() : '';
    },

    selectorValue: function(element)
    {
        var selector = this.selector(element);
        return selector !== undefined ? selector.val() : null;
    },

    selector: function(element) {
        return this._selector;
    },

    selectorModel: function(element, key)
    {
        var models = this.selectorModels(element);

        for(var i in models)
        {
            var model = models[i];

            //console.log('model:', model.pattern, 'key:', key, 'match:', key.match(model.pattern), 'content:', model.content.pattern);

            if (typeof key === 'string' && key.match(model.pattern) !== null) {
                return model.content.render(this._context);
            }
        }
    },

    selectorModels: function(element) {
        return this._models || [];
    },

    dependencies: function(element) {
        return (this._selectorKey ? this._selectorKey.tags() : []).concat(this._dependencies);
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        var previous_key = this.selectorKey(element);

        this._context = $.extend({}, this._context || {}, data || {});
        this._selectorKey.update(data);
        this.toggleSelector(element, previous_key, cb, error_cb, sync);
    },

    reset: function(element)
    {
        if (this._selector) {
            this._selector.reset();
        }
    },

    val: function(element, value)
    {
        if (value === undefined)
            return this._selector ? this._selector.val() : null;

        if (this._selector) {
            this._selector.val(value);
        }
    }
});
