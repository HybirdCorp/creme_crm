/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2022 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

creme.form = creme.form || {};

var S2 = $.fn.select2.amd;

function djangoLocalisation(options) {
    return {
        errorLoading: function () {
            return options.errorLoadingMsg || gettext('The results could not be loaded.');
        },
        inputTooLong: function (args) {
            var overChars = args.input.length - args.maximum;

            if (options.inputTooLongMsg) {
                return options.inputTooLongMsg(args);
            } else {
                return ngettext('Please delete %d character', 'Please delete %d characters', overChars).format(overChars);
            }
        },
        inputTooShort: function (args) {
            var remainingChars = args.minimum - args.input.length;

            if (options.inputTooShortMsg) {
                return options.inputTooShortMsg(args);
            } else {
                return ngettext('Please enter %d or more characters', 'Please enter %d or more characters', remainingChars).format(remainingChars);
            }
        },
        loadingMore: function () {
            return options.loadingMoreMsg || gettext('Loading more results…');
        },
        enumTooManyResults: function() {
            return options.tooManyResults || gettext('Show more results');
        },
        maximumSelected: function (args) {
            if (options.maximumSelectedMsg) {
                return options.maximumSelectedMsg(args);
            } else {
                return ngettext('You can only select %d item', 'You can only select %d items', args.maximum).format(args.maximum);
            }
        },
        noResults: function () {
            return options.noResultsMsg || gettext('No result');
        },
        searching: function () {
            return options.searchingMsg || gettext('Searching…');
        },
        removeAllItems: function () {
            return options.removeAllItemsMsg || gettext('Remove all items');
        },
        removeItem: function () {
            return options.removeItemMsg || gettext('Remove item');
        },
        search: function() {
            return options.searchMsg || gettext('Search');
        }
    };
}

function convertToSelect2Data(data) {
    data = data || [];

    var groups = {};
    var options = [];

    data.filter(function(item) {
        return item.visible !== false;
    }).forEach(function(item) {
        var option = {
            id: item.value,
            text: item.label,
            disabled: item.disabled || false,
            selected: item.selected || false
        };

        if (item.group) {
            var group = groups[item.group] = (groups[item.group] || {
                text: item.group,
                children: []
            });

            group.children.push(option);
        } else {
            options.push(option);
        }
    });

    if (!_.isEmpty(groups)) {
        options = options.concat(_.values(groups));
    }

    return options;
}

S2.define('select2/data/enum', [
    'select2/data/array',
    'select2/utils'
], function(ArrayAdapter, Utils) {
    function Adapter(element, options) {
        var enumOptions = this.enumOptions = $.extend({
            limit: 50,
            debounce: 100,
            cache: false
        }, options.get('enum'));

        if (enumOptions.cache) {
            this._queryBackend = creme.ajax.defaultCacheBackend();
        } else {
            this._queryBackend = creme.ajax.defaultBackend();
        }

        Adapter.__super__.constructor.call(this, element, options);
    };

    Utils.Extend(Adapter, ArrayAdapter);

    Adapter.prototype.bind = function (container, $container) {
        Adapter.__super__.bind.call(this, container, $container);

        var self = this;

        this._pinItems = this.$element.find('option[data-pinned]')
                                      .map(function() { return self.item($(this)); })
                                      .get();

        container.on('enum:more', function(params) {
            params = $.extend({}, this._lastEnumParams);
            params.limit += this.enumOptions.limit;
            this.trigger('query', params);
        }.bind(this));


        container.on('close', function() {
            // If some queries were already done, think to reset the limit !
            if (this._lastEnumParams) {
                this._lastEnumParams.limit = this.enumOptions.limit;
            }
        }.bind(this));
    };

    Adapter.prototype.processResults = function (data, limit) {
        var items = (this._pinItems || []).concat(convertToSelect2Data(data));

        return {
            results: items.slice(0, limit),
            more: data.length > limit
        };
    };

    Adapter.prototype.enumQuery = function (params, callback) {
        var self = this;
        var options = this.enumOptions;

        params.limit = (params.limit || this.enumOptions.limit);

        if (this._query && this._query.isCancelable()) {
            this._query.cancel();
        }

        var query = this._query = this._queryBackend.query({backend: {dataType: 'json'}});

        query.url(options.url)
             .onDone(function(event, data) {
                 self._lastEnumParams = params;
                 callback(self.processResults(data, params.limit));
             })
             .onFail(function() {
                 self.trigger('results:message', {
                     message: 'errorLoading'
                 });
             });

        return query.get({
            term: params.term,
            limit: params.limit + 1  // Ask for one more element to detect overflow
        });
    };

    Adapter.prototype.query = function (params, callback) {
        /*
         * HACK : underscoreJS function _.debounce does not work within Select2 "context"
         * for whatever reason. Lets do it ourselves !
         */
        if (this._debounce) {
            clearTimeout(this._debounce);
        }

        if (this.enumOptions.debounce > 0) {
            this._debounce = setTimeout(function() {
                this._debounce = null;
                this.enumQuery(params, callback);
            }.bind(this), this.enumOptions.debounce);
        } else {
            this.enumQuery(params, callback);
        }
    };

    return Adapter;
});


S2.define('select2/dropdown/enum', [], function () {
    function EnumMessage(decorated, $element, options, dataAdapter) {
        decorated.call(this, $element, options, dataAdapter);
        this.$message = this.createMessage();
    }

    EnumMessage.prototype.bind = function (decorated, container, $container) {
        decorated.call(this, container, $container);

        var self = this;

        this.$results.parent().on('click', '.select2-results__more', function(e) {
            e.stopPropagation();
            self.moreLoading = true;
            self.trigger('enum:more');
        });

        container.on('query', function() {
            self.$message.remove();
        });
    };

    EnumMessage.prototype.append = function (decorated, data) {
        decorated.call(this, data);

        this.moreLoading = false;

        if (data.more) {
            this.$results.parent().append(this.$message);
        } else {
            this.$message.remove();
        }
    };

    EnumMessage.prototype.createMessage = function() {
        var message = this.options.get('translations').get('enumTooManyResults');
        var element = $(
            '<div class="select2-results__more" role="option" aria-disabled="true"></div>'
        );

        element.html(message({}));
        return element;
    };

    return EnumMessage;
});


creme.form.Select2 = creme.component.Component.sub({
    _init_: function(element, options) {
        Assert.not(element.is('.select2-hidden-accessible'), 'Select2 instance is already active');

        options = this._options = $.extend({
            multiple: element.is('[multiple]'),
            sortable: element.is('[sortable]'),
            allowClear: element.data('allowClear'),
            placeholder: element.data('placeholder'),
            placeholderMultiple: element.data('placeholderMultiple'),
            enumURL: element.data('enumUrl'),
            enumLimit: element.data('enumLimit'),
            enumDebounce: element.data('enumDebounce'),
            enumCache: element.data('enumCache')
        }, options || {});

        var placeholder = options.multiple ? options.placeholderMultiple : options.placeholder;

        var select2Options = {
            allowClear: options.allowClear,
            placeholder: placeholder,
            debug: true,
            theme: 'creme',
            language: this.localisation(),
            templateSelection: function(data) {
                return data.text;
            }
        };

        if (options.enumURL) {
            S2.require([
                'select2/utils',
                'select2/results',
                'select2/data/enum',
                'select2/dropdown/enum',
                'select2/dropdown/hidePlaceholder'
            ], function(Utils, ResultsAdapter, EnumAdapter, EnumMessage, HidePlaceholder) {
                var resultsAdapter = Utils.Decorate(ResultsAdapter, EnumMessage);

                if (select2Options.placeholder) {
                    resultsAdapter = Utils.Decorate(resultsAdapter, HidePlaceholder);
                }

                $.extend(select2Options, {
                    'enum': {
                        url: options.enumURL,
                        debounce: options.enumDebounce,
                        limit: options.enumLimit,
                        cache: options.enumCache
                    },
                    dataAdapter: EnumAdapter,
                    resultsAdapter: resultsAdapter
                });
            }, undefined, true);
        }

        if (select2Options.placeholder && Object.isEmpty(element.find('option[value=""]'))) {
            element.append($('<option>${placeholder}</option>'.template(select2Options)));
        }

        var instance = element.select2(select2Options);

        if (options.multiple && options.sortable) {
            this._activateSort(element);
        }

        this._instance = instance;
        this.element = element;
        return this;
    },

    options: function() {
        return $.extend({}, this._options);
    },

    localisation: function(options) {
        return djangoLocalisation($.extend({}, this._options, options));
    },

    destroy: function() {
        if (!Object.isNone(this.element)) {
            if (this._sortable && this._sortable.length > 0) {
                this._sortable.sortable('destroy');
                this._sortable = null;
            }

            this.element.select2('destroy');
            this._instance = null;
            this.element = null;
        }

        return this;
    },

    refresh: function() {
        var data = creme.model.ChoiceGroupRenderer.parse(this.element);

        this.element.select2({
            data: convertToSelect2Data(data)
        });

        this.element.trigger('change.select2');
        return this;
    },

    _activateSort: function(element) {
        var choices = element.next('.select2-container').parent();

        this._sortable = choices.sortable({
            items: '.select2-selection__choice',
            // tolerance: 'pointer',
            opacity: 0.5,
            revert:  200,
            delay:   200,
            stop: function() {
                S2.require(['select2/utils'], function(Utils) {
                    var sorted = $(choices).find('.select2-selection__choice').map(function() {
                        return Utils.GetData(this, 'data');
                    }).get().map(function(d) {
                        return d.id;
                    });

                    element.val(sorted);
                });
            }
        });
    }
});

}(jQuery));
