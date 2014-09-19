/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

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

creme.widget = creme.widget || {};

creme.widget.DYNAMIC_SELECT_BACKEND = new creme.ajax.CacheBackend(new creme.ajax.Backend(),
                                                                  {condition: new creme.ajax.CacheBackendTimeout(120 * 1000)});

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        backend: creme.widget.DYNAMIC_SELECT_BACKEND, //new creme.ajax.Backend({dataType:'json', sync:true}),
        datatype: 'string',
        url: '',
        filter: '',
        dependencies: '',
        multiple: undefined,
        sortable: undefined,
        autocomplete: undefined,
        'autocomplete-options': ''
    },

    _create: function(element, options, cb, sync)
    {
        this._context = {}
        this._backend = options.backend;
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._url = new creme.utils.Template(options.url);
        this._filter = new creme.utils.Template(options.filter);
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);

        this._init_model(element, options);
        this._init_autocomplete(element, options);

        this.reload(element, {}, cb, cb, sync);

        element.addClass('widget-ready');
    },

    _destroy: function(element)
    {
        if (this._autocomplete) {
            this._autocomplete.deactivate(element);
        }
    },

    _init_model: function(element, options)
    {
        var self = this;
        var converter = this._converter = options.datatype === 'json' ? function(data) {return creme.widget.cleanval(data, null)} : undefined;
        var initial = creme.model.ChoiceRenderer.parse(element, converter);

        this._model_onchange_cb = function() {
            self._onModelChange(element);
        };

        this._model = new creme.model.AjaxArray(this._backend, initial);
        this._model.url(function() {return self.url();})
                   .converter(this._modelConverter)
                   .comparator(this._modelComparator);

        this._filtered = new creme.model.Filter(this._model);
        this._filtered.bind(['remove', 'clear', 'reset', 'add'], this._model_onchange_cb);

        this._renderer = new creme.model.ChoiceRenderer(element, this._filtered);
    },

    _init_autocomplete: function(element, options)
    {
        if (Object.isNone(options.autocomplete))
            return;

        try {
            chosen_options = options['autocomplete-options'] || '';
            chosen_options = chosen_options.length ? creme.object.build_callback(chosen_options)() : {};
        } catch(e) {
            chosen_options = {};
        }

        var chosen_options = $.extend({
            multiple: options.multiple !== undefined,
            sortable: options.sortable !== undefined
        }, chosen_options)

        this._autocomplete = new creme.component.Chosen(chosen_options);
        this._autocomplete.activate(element);
    },

    _updateDisabledState: function(element)
    {
        var disabled = !($('option:not(:disabled)', element).length > 1 && this._enabled);
        element.toggleAttr('disabled', disabled);
    },

    _updateAutocomplete: function()
    {
        if (this._autocomplete) {
            this._autocomplete.refresh();
        }
    },

    _onModelChange: function(element, old)
    {
        this._updateDisabledState(element);
        this._updateAutocomplete();
    },

    _modelConverter: function(data)
    {
        return data ? data.map(function(entry) {
            return Array.isArray(entry) ? {value: entry[0], label: entry[1]} : {value: entry, label: '' + entry};
        }) : [];
    },

    _modelComparator: function(a, b) {
        return a.value < b.value ? -1 : (a.value > b.value ? 1 : 0);
    },

    _updateModel: function(element, cb, error_cb, sync)
    {
        var self = this;
        var url = this.url();

        if (!url)
        {
            this._onModelChange(element);
            creme.object.invoke(error_cb, element, new creme.ajax.AjaxResponse('404', ''));
            return;
        }

        var selected = this.val(element);

        this._model.fetch({fields:['id', 'unicode']}, {dataType:'json', sync:sync}, {
            done:  function(event, data) {
                self.val(element, selected);
                creme.object.invoke(cb, element, data);
            },
            fail:  function(event, data, error) {
                self.val(element, selected);
                creme.object.invoke(error_cb, element, error);
            },
            cancel: function(event, data) {
                self.val(element, selected);
            }
        });
    },

    _updateFilter: function(element)
    {
        var self = this;
        var filter = this.filter(element);
        var selected = this.val(element);

        if (this._previousFilter === filter) {
            this._filtered.fetch();
            this.val(element, selected);
            return;
        }

        this._previousFilter = filter;

        var lambda = creme.utils.lambda(filter, 'item, context', null);
        this._filtered.filter(lambda !== null ? function(item) {return lambda(item, self._context);} : null);

        this.val(element, selected);
        return;
    },

    filter: function(element, filter)
    {
        if (filter === undefined)
            return this._filter && this._filter.iscomplete() ? this._filter.render() : '';

        this._filter = new creme.utils.Template(filter);
        this._filter.update(this._context || {});
        this._updateFilter(element);
        return this;
    },

    url: function(element, url)
    {
        if (url === undefined)
            return this._url && this._url.iscomplete() ? this._url.render() : '';

        this._url = new creme.utils.Template(url);
        this._url.update(this._context || {});
        this._updateModel(element);
        return this;
    },

    dependencies: function(element) {
        return this._dependencies.concat(this._url.tags() || []).concat(this._filter.tags() || []);
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        var self = this;
        var data = data || {};

        this._context = $.extend({}, this._context || {}, data);
        this._url.update(data);
        this._filter.update(data);

        this._updateFilter(element);
        this._updateModel(element, cb, error_cb, sync);

        return this;
    },

    update: function(element, data)
    {
        var data = creme.widget.cleanval(data, {});

        this._model.patch({
                            add:    this._modelConverter(data.added),
                            remove: this._modelConverter(data.removed)
                          });

        this.val(element, data.value);
        return this;
    },

    model: function(element) {
        return this._model;
    },

    _onSelectionChange: function(element, previous)
    {
        // Chrome behaviour (bug ?) : select value is not updated if disabled.
        // so enable it before change value !
        element.removeAttr('disabled');
        element.change();

        this._updateDisabledState(element);
        this._updateAutocomplete();
    },

    val: function(element, value)
    {
        if (value === undefined)
            return element.val();

        var old = element.val();

        if (value !== null && typeof value !== 'string') {
            value = $.toJSON(value);
        }

        if (value !== null && this.choice(element, value) === undefined) {
            this.selectfirst(element);
        } else {
            element.val(value);
        }

        this._onSelectionChange(element);
    },

    cleanedval: function(element)
    {
        var value = this.val(element);

        if (this.options.datatype === 'string')
            return value;

        return this._converter ? this._converter(value) : value;
    },

    reset: function(element) {
        this.selectfirst(element);
    },

    selectfirst: function(element)
    {
        element.val($('option:not(:disabled):first', element).attr('value'));
        this._onSelectionChange(element);
    },

    firstchoice: function(element)
    {
        var choices = $('option:not(:disabled):first', element);
        return choices.length ? [choices.attr('value'), choices.text()] : null;
    },

    _querychoices: function(element, key)
    {
        if (typeof key !== 'string') {
            key = $.toJSON(key);
        }

        var choices = $('option' + (key ? ':not(:disabled)' : ''), element).filter(function() {
            return $(this).parents('select:first').is(element);
        });

        return !Object.isEmpty(key) ? choices.filter(function() {return $(this).attr('value') === key;}) : choices;
    },

    _querygroups: function(element, key)
    {
        if (typeof key !== 'string') {
            key = $.toJSON(key);
        }

        var groups = $('optgroup' + (key ? ':not(:disabled)' : ''), element).filter(function() {
            return $(this).parents('select:first').is(element);
        });

        return !Object.isEmpty(key) ? groups.filter(function() {return $(this).attr('label') === key;}) : groups;
    },

    choice: function(element, key)
    {
        if (Object.isNone(key) === true)
            return;

        var choices = this._querychoices(element, key);

        // IE8 strange behaviour (jquery bug ?) that returns key instead of undefined when choice doesn't exist.
        // Fix it with jquery result length check.
        return choices.length ? [key, choices.text()] : undefined;
    },

    choices: function(element)
    {
        var choices = [];

        this._querychoices(element).each(function() {
            choices.push([$(this).attr('value'), $(this).text()]);
        });

        return choices;
    },

    groups: function(element)
    {
        var groups = [];

        this._querygroups(element).each(function() {
            return groups.push($(this).attr('label'));
        });

        return groups;
    },

    selected: function(element) {
        return this.choice(element, this.val(element));
    }
});

