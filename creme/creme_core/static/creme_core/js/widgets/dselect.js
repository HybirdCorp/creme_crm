/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

creme.widget = creme.widget || {};

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        backend: undefined, // new creme.ajax.Backend({dataType:'json', sync:true}),
        datatype: 'string',
        url: '',
        filter: '',
        dependencies: '',
        multiple: undefined,
        sortable: undefined,
        autocomplete: undefined,
        'autocomplete-options': ''
    },

    _create: function(element, options, cb, sync) {
        this._context = {};
        this._backend = options.backend || creme.ajax.defaultCacheBackend();
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._readonly = creme.object.isTrue(options.readonly) && element.is('[readonly]');
        this._multiple = creme.object.isTrue(options.multiple) && element.is('[multiple]');
        this._url = new creme.utils.Template(options.url);
        this._filter = new creme.utils.Template(options.filter);
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);

        this._init_model(element, options);
        this._init_autocomplete(element, options);

        this.reload(element, {}, cb, cb, sync);

        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        if (this._autocomplete) {
            this._autocomplete.deactivate();
        }
    },

    _init_model: function(element, options) {
        var self = this;
        var converter = this._converter = options.datatype === 'json' ? function(data) { return creme.widget.cleanval(data, null); } : undefined;
        var initial = creme.model.ChoiceGroupRenderer.parse(element, converter);

        this._model_onchange_cb = function() {
            self._onModelChange(element);
        };

        this._model = new creme.model.AjaxArray(this._backend, initial);
        this._model.url(function() { return self.url(); })
                   .converter(this._modelConverter)
                   .comparator(this._modelComparator);

        this._filtered = new creme.model.Filter(this._model);
        this._filtered.bind(['remove', 'clear', 'reset', 'add'], this._model_onchange_cb);

        this._renderer = new creme.model.ChoiceGroupRenderer(element, this._filtered);
    },

    _init_autocomplete: function(element, options) {
        if (Object.isNone(options.autocomplete)) {
            return;
        }

        var chosen_options = {};

        try {
            chosen_options = options['autocomplete-options'] || '';
            chosen_options = chosen_options.length ? creme.object.build_callback(chosen_options)() : {};
        } catch (e) {
            chosen_options = {};
        }

        chosen_options = $.extend({
            multiple: options.multiple !== undefined,
            sortable: options.sortable !== undefined,
            search_contains: true
        }, chosen_options);

        this._autocomplete = new creme.component.Chosen(chosen_options);
        this._autocomplete.activate(element);
    },

    _updateDisabledState: function(element) {
        var active_option_count = $('option:not(:disabled)', element).length;
        var is_empty = active_option_count < 1;
        var is_single = active_option_count < 2;

        var disabled = !this._enabled || is_empty;
        var readonly = (is_single && !this._multiple) || this._readonly;

        element.prop('disabled', disabled);
        element.toggleAttr('readonly', readonly);
    },

    _updateAutocomplete: function() {
        if (this._autocomplete) {
            this._autocomplete.refresh();
        }
    },

    _onModelChange: function(element, old) {
        this._updateDisabledState(element);
        this._updateAutocomplete();
    },

    _modelConverter: function(rawdata) {
        var data = creme.model.ChoiceGroupRenderer.choicesFromTuples(rawdata);

        // HACK : render helptext as label.
        return data.map(function(entry) {
            var label = entry.label;

            if (entry.help || entry.group) {
                label = '<span>${label}</span>'.template(entry);

                if (entry.help) {
                    label += '<span class="group-help">${help}</span>'.template(entry);
                }

                if (entry.group) {
                    label += '<span class="hidden">${group}</span>'.template(entry);
                }
            }

            entry.label = label;
            return entry;
        });
    },

    _modelComparator: function(a, b) {
        return a.value < b.value ? -1 : (a.value > b.value ? 1 : 0);
    },

    _updateModel: function(element, cb, error_cb, sync) {
        var self = this;
        var url = this.url();

        if (url === null) {
            this._model.reset([]);
            return;
        }

        // TODO : a bit strange behaviour, remove it later
        if (!url) {
            this._onModelChange(element);
            creme.object.invoke(error_cb, element, new creme.ajax.AjaxResponse('404', ''));
            return;
        }

        var selected = this.val(element);

        this._model.fetch({fields: ['id', 'unicode'], sort: 'unicode'}, {backend: {dataType: 'json', sync: sync}}, {
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

    _updateFilter: function(element) {
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
        this._filtered.filter(lambda !== null ? function(item) { return lambda(item, self._context); } : null);

        this.val(element, selected);
    },

    filter: function(element, filter) {
        if (filter === undefined) {
            return this._filter && this._filter.iscomplete() ? this._filter.render() : '';
        }

        this._filter = new creme.utils.Template(filter);
        this._filter.update(this._context || {});
        this._updateFilter(element);
        return this;
    },

    url: function(element, url) {
        if (url === undefined) {
            return this._url && this._url.iscomplete() ? this._url.render() : null;
        }

        this._url = new creme.utils.Template(url);
        this._url.update(this._context || {});
        this._updateModel(element);
        return this;
    },

    dependencies: function(element) {
        return this._dependencies.concat(this._url.tags() || []).concat(this._filter.tags() || []);
    },

    reload: function(element, data, cb, error_cb, sync) {
        data = data || {};

        this._context = $.extend({}, this._context || {}, data);
        this._url.update(data);
        this._filter.update(data);

        this._updateFilter(element);
        this._updateModel(element, cb, error_cb, sync);

        return this;
    },

    update: function(element, data) {
        data = creme.widget.cleanval(data, {});
        var model = this._model;
        var duplicates = function(item) {
            return model.indexOf(item) === -1;
        };

        model.patch({
            add:    this._modelConverter(data.added).filter(duplicates),
            remove: this._modelConverter(data.removed)
        });

        this.val(element, data.value);
        return this;
    },

    model: function(element) {
        return this._model;
    },

    _onSelectionChange: function(element, previous) {
        // Chrome behaviour (bug ?) : select value is not updated if disabled.
        // so enable it before change value !
        element.prop('disabled', false);
        element.trigger('change');

        this._updateDisabledState(element);
        this._updateAutocomplete();
    },

    // TODO : find a more generic way for this !
    _valMultiple: function(element, value) {
        if (value === undefined) {
            return element.val();
        }

        if (value !== null) {
            var selections = [];

            if (Object.isString(value)) {
                selections = creme.utils.JSON.clean(value, value.split(','));
            } else {
                selections = value;
            }

            selections = Array.isArray(selections) ? selections : [selections];
            selections = selections.map(function(item) {
                return Object.isString(item) === false ? JSON.stringify(item) : item;
            });

            element.val(selections);
            this._onSelectionChange(element);
        }
    },

    val: function(element, value) {
        if (this.options.multiple) {
            return this._valMultiple(element, value);
        }

        if (value === undefined) {
            return element.val();
        }

        value = value !== null ? value : '';

        if (Object.isString(value) === false) {
            value = JSON.stringify(value);
        }

        var choice = this.choice(element, value);

        if (choice === undefined) {
            this.selectfirst(element);
        } else {
            element.val(value);
            this._onSelectionChange(element);
        }
    },

    cleanedval: function(element) {
        var value = this.val(element);

        if (this.options.datatype === 'string') {
            return value;
        }

        if (this.options.multiple) {
            return this._converter ? value.map(this._converter) : value;
        }

        return this._converter ? this._converter(value) : value;
    },

    reset: function(element) {
        this.selectfirst(element);
    },

    selectfirst: function(element) {
//        element.val($('option:not(:disabled):first', element).attr('value'));
        element.val($('option:not(:disabled)', element).first().attr('value'));
        this._onSelectionChange(element);
    },

    firstchoice: function(element) {
//        var choices = $('option:not(:disabled):first', element);
        var choices = $('option:not(:disabled)', element).first();
        return choices.length ? [choices.attr('value'), choices.text()] : null;
    },

    _querychoices: function(element, key, strict) {
        if (Object.isString(key) === false) {
            key = JSON.stringify(key);
        }

        var choices = $('option' + (key ? ':not(:disabled)' : ''), element).filter(function() {
//            return $(this).parents('select:first').is(element);
            return $(this).parents('select').first().is(element);
        });

        if (Object.isEmpty(key) && !strict) {
            return choices;
        }

        return choices.filter(function() {
            return $(this).attr('value') === key;
        });
    },

    _querygroups: function(element, key, strict) {
        if (Object.isString(key) === false) {
            key = JSON.stringify(key);
        }

        var groups = $('optgroup' + (key ? ':not(:disabled)' : ''), element).filter(function() {
//            return $(this).parents('select:first').is(element);
            return $(this).parents('select').first().is(element);
        });

        if (Object.isEmpty(key) && !strict) {
            return groups;
        }

        return groups.filter(function() {
            return $(this).attr('label') === key;
        });
    },

    choice: function(element, key) {
        if (Object.isNone(key) === true) {
            return;
        }

        var choices = this._querychoices(element, key, true);

        // IE8 strange behavior (jquery bug ?) that returns key instead of undefined when choice doesn't exist.
        // Fix it with jquery result length check.
        return choices.length > 0 ? [key, choices.first().text()] : undefined;
    },

    choices: function(element) {
        var choices = [];

        this._querychoices(element).each(function() {
            choices.push([$(this).attr('value'), $(this).text()]);
        });

        return choices;
    },

    groups: function(element) {
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

}(jQuery));
