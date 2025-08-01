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

creme.widget = creme.widget || {};

function datatypeConverter(datatype) {
    if (datatype === 'json') {
        return function(data) {
            return creme.widget.cleanval(data, null);
        };
    }
}

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        backend: undefined, // new creme.ajax.Backend({dataType:'json', sync:true}),
        datatype: 'string',
        url: '',
        filter: '',
        dependencies: '',
        multiple: false,
        sortable: false,
        autocomplete: false
    },

    _create: function(element, options, cb, sync) {
        this._context = {};

        this._backend = options.backend || creme.ajax.defaultCacheBackend();
        this._enabled = creme.object.isFalse(options.disabled) && !element.prop('disabled');
        this._readonly = creme.object.isTrue(options.readonly) || element.is('.is-readonly');
        this._multiple = creme.object.isTrue(options.multiple) && element.is('[multiple]');
        this._autocomplete = creme.object.isTrue(options.autocomplete) || element.is('[autocomplete]');
        this._url = new creme.utils.Template(options.url);
        this._filter = new creme.utils.Template(options.filter);
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);

        this.cacheMode(element, options.cache || element.data("cache") || 'full');
        this.noEmpty(element, options.noEmpty || element.data('noEmpty'));

        this._initModel(element, options);
        this._initAutocomplete(element, options);
        this._updateDisabledState(element);

        this.reload(element, {}, cb, cb, sync);

        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        if (this._select2) {
            this._select2.destroy();
        }
    },

    _initModel: function(element, options) {
        var self = this;
        var converter = this._converter = datatypeConverter(options.datatype);
        var initial = creme.model.ChoiceGroupRenderer.parse(element, converter);

        this._model = new creme.model.AjaxArray(this._backend, initial);
        this._model.url(function() { return self.url(); })
                   .converter(this._modelConverter)
                   .comparator(this._modelComparator);

        this._filtered = new creme.model.Filter(this._model);
        this._filtered.bind('remove clear reset add', function() {
                          self._onModelChange(element);
                       })
                      .bind('clear reset', function() {
                          self._onModelReset(element);
                       });

        this._renderer = new creme.model.ChoiceGroupRenderer(element, this._filtered);
    },

    _initAutocomplete: function(element, options) {
        if (this._autocomplete) {
            this._select2 = new creme.form.Select2(element, {
                multiple: Boolean(this._multiple),
                sortable: element.is('[data-sortable]'),
                noResultsMsg: element.data('noResults'),
                placeholder: element.data('placeholder'),
                placeholderMultiple: element.data('placeholderMultiple'),
                noEmpty: this.noEmpty(element)
            });
        }
    },

    _updateAutocomplete: function(element) {
        if (this._select2) {
            this._select2.refresh();
        }
    },

    _updateDisabledState: function(element) {
        var active_option_count = $('option:not(:disabled)', element).length;
        var is_empty = active_option_count < 1;
        var is_single = active_option_count < 2;

        var disabled = !this._enabled || is_empty;
        var readonly = (is_single && !this._multiple) || this._readonly;

        element.prop('disabled', disabled);
        element.toggleClass('is-readonly', readonly);
    },

    _onModelChange: function(element) {
        this._updateDisabledState(element);
    },

    _onModelReset: function(element) {
        this._updateAutocomplete(element);
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

        this._model.fetch({
            fields: ['id', 'unicode'],
            sort: 'unicode'
        }, {
            backend: {
                dataType: 'json',
                sync: sync,
                forcecache: this._forceCache
            }
        }, {
            done:  function(event, data) {
                self._forceCache = (self.cacheMode() === 'ignore');
                self.val(element, selected);
                creme.object.invoke(cb, element, data);
            },
            fail:  function(event, data, error) {
                self.val(element, selected);
                creme.object.invoke(error_cb, element, error);
            },
            cancel: function(event, data) {
                // self.val(element, selected);
            }
        });
    },

    _updateFilter: function(element) {
        var self = this;
        var filter = this.filter(element);

        if (this._previousFilter === filter) {
            this._filtered.fetch();
            return;
        }

        this._previousFilter = filter;

        var lambda = creme.utils.lambda(filter, 'item, context', null);
        this._filtered.filter(lambda !== null ? function(item) { return lambda(item, self._context); } : null);
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
        var notInModel = function(item) {
            return model.indexOf(item) === -1;
        };

        model.patch({
            add:    this._modelConverter(data.added).filter(notInModel),
            remove: this._modelConverter(data.removed)
        });

        this.val(element, data.value);
        return this;
    },

    model: function(element) {
        return this._model;
    },

    cacheMode: function(element, mode) {
        if (mode === undefined) {
            return this._cacheMode;
        }

        Assert.in(mode, ['ignore', 'force', 'full']);

        this._forceCache = (mode !== 'full');
        this._cacheMode = mode;
        return this;
    },

    noEmpty: function(element, value) {
        if (value === undefined) {
            return this._noEmpty;
        }

        this._noEmpty = creme.object.isTrue(value);

        if (this._select2) {
            this._select2.noEmpty(this._noEmpty);
        }

        return this;
    },

    _onSelectionChange: function(element, previous) {
        // Chrome behaviour (bug ?) : select value is not updated if disabled.
        // so enable it before change value !
        element.prop('disabled', false);
        element.trigger('change');

        this._updateDisabledState(element);
    },

    _select: function(element, value) {
        var selected = [];
        var isMultiple = this.options.multiple;
        var isJSON = this.options.datatype === 'json';
        var previous = element.val();

        if (isMultiple) {
            if (Object.isString(value)) {
                /*
                 * A string value. can be :
                 *   - JSON array
                 *   - JSON object
                 *   - comma separated string
                 */
                var values = value.split(',');
                selected = isJSON ? _.cleanJSON(value) || values : values;
            } else {
                selected = value;
            }

            /* Can be an Object or an Array -> convert to Array */
            selected = Array.isArray(selected) ? selected : [selected];
        } else {
            selected = [value];
        }

        /* Convert all non-string data into JSON or regular strings */
        if (isJSON) {
            selected = _.reject(selected, Object.isNone).map(function(item) {
                return !Object.isString(item) ? JSON.stringify(item) : item;
            });
        } else {
            selected = _.reject(selected, Object.isNone).map(function(item) {
                return String(item);
            });
        }

        /*
         * Select2 have it own way to deal with selection because paged enums
         * can add missing options available on other pages.
         */
        if (this._select2) {
            this._select2.select(selected);
            this._onSelectionChange(element, previous);
        } else {
            /*
             * Specific behavior designed for the chained select.
             * In single value mode, fallback on first option if the selected one is invalid or empty.
             */
            if (!isMultiple && this.noEmpty(element)) {
                // Filter all the existing values
                if (selected.length > 0) {
                    var available = new Set(
                        element.find('option:not(:disabled)').map(function() {
                            return $(this).attr('value');
                        })
                    );

                    selected = selected.filter(function(value) {
                        return available.has(value);
                    });
                }

                // If empty and not multiple select the first option.
                if (selected.length === 0) {
                    var first = $('option:not(:disabled)', element).first().attr('value');
                    selected = Object.isNone(first) ? [] : [first];
                }
            }

            element.val(isMultiple ? selected : (selected[0] || null));
            this._onSelectionChange(element, previous);
        }
    },

    val: function(element, value) {
        if (value === undefined) {
            return element.val();
        }

        this._select(element, value);
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
        var value = $('option:not(:disabled)', element).first().attr('value');
        this._select(element, value);
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
        return this._querychoices(element).get().map(function(item) {
            return [$(item).attr('value'), $(item).text()];
        });
    },

    groups: function(element) {
        return this._querygroups(element).get().map(function(item) {
            return $(item).attr('label');
        });
    },

    selected: function(element) {
        return this.choice(element, this.val(element));
    }
});

}(jQuery));
