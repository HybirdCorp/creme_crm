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
        createItem: function (args) {
            if (options.createItemMsg) {
                return options.createItemMsg(args);
            } else {
                return gettext('Create new item «%s»').format(args.label);
            }
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

function renderSelect2Result(state) {
    if (state.pinned) {
        return $(
           '<span class="select2-results__pin">${text}</span>'.template(state)
        );
    } else {
        return state.text;
    }
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

    Adapter.prototype.pinItem = function($options) {
        var data = this.item($options);
        data.pinned = true;
        return data;
    };

    Adapter.prototype.bind = function (container, $container) {
        Adapter.__super__.bind.call(this, container, $container);

        var self = this;

        this._pinItems = this.$element.find('option[data-pinned]')
                                      .map(function() { return self.pinItem($(this)); })
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

S2.define('select2/dropdown/creator', [], function () {
    function CreatorButton(decorated, $element, options, dataAdapter) {
        decorated.call(this, $element, options, dataAdapter);
        this.$button = this.createButton();
        this._dataAdapter = dataAdapter;
    }

    CreatorButton.prototype.bind = function (decorated, container, $container) {
        decorated.call(this, container, $container);

        var self = this;

        this.$results.parent().on('click', '.select2-results__create', function(e) {
            e.stopPropagation();

            var text = self._lastCreatorText;
            var form = new creme.dialog.FormDialog({
                url: self.options.get('creatorURL')
            });

            form.one('frame-update', function(event, frame) {
                frame.delegate().find('input[type="text"]:first').val(text);
            });

            form.onFormSuccess(function(event, response, dataType) {
                var items = ((response.data() || {}).added || []);

                self.addItems(items.map(function(item) {
                    return {
                        id: item[0],
                        text: item[1]
                    };
                }));
            });

            self.trigger('close');
            form.open();
        });

        container.on('results:all', function(params) {
            var term = params.query.term;
            var texts = params.data.results.map(function(item) {
                return item.text;
            });

            if (term && texts.indexOf(term) === -1) {
                var message = this.options.get('translations').get('createItem');

                this.$button.find('.select2-results__create-title')
                            .html(message({label: term}));

                this.$results.parent().append(self.$button);
                this._lastCreatorText = term;
            } else {
                this.$button.remove();
                this._lastCreatorText = null;
            }
        }.bind(this));

        container.on('close', function() {
            this.$button.remove();
            this._lastCreatorText = null;
        }.bind(this));
    };

    CreatorButton.prototype.addItems = function(decorated, items) {
        var dataAdapter = this._dataAdapter;

        var options = (items || []).map(function(item) {
            var $option = dataAdapter.option(dataAdapter._normalizeItem(item));
            $option[0].selected = true;
            return $option;
        });

        dataAdapter.addOptions(options);
    };

    CreatorButton.prototype.createButton = function(label) {
        return $(
            '<div class="select2-results__create">' +
                '<span class="select2-results__create-icon">+</span>' +
                '<span class="select2-results__create-title"></span>' +
            '</div>'
        );
    };

    return CreatorButton;
});

creme.form.Select2 = creme.component.Component.sub({
    _init_: function(element, options) {
        Assert.not(element.is('.select2-hidden-accessible'), 'Select2 instance is already active');

        options = this._options = $.extend(true, {
            multiple: element.is('[multiple]'),
            sortable: element.is('[sortable]'),
            allowClear: element.data('allowClear'),
            placeholder: element.data('placeholder'),
            placeholderMultiple: element.data('placeholderMultiple'),
            createURL: element.data('createUrl'),
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

        S2.require([
            'select2/utils',
            'select2/results',
            'select2/data/enum',
            'select2/dropdown/enum',
            'select2/dropdown/creator',
            'select2/dropdown/hidePlaceholder'
        ], function(Utils, ResultsAdapter, EnumAdapter, EnumMessage, CreatorButton, HidePlaceholder) {
            var resultsAdapter = ResultsAdapter;

            if (placeholder) {
                resultsAdapter = Utils.Decorate(resultsAdapter, HidePlaceholder);
            }

            if (options.createURL) {
                resultsAdapter = Utils.Decorate(resultsAdapter, CreatorButton);
            }

            if (options.enumURL) {
                resultsAdapter = Utils.Decorate(resultsAdapter, EnumMessage);

                $.extend(select2Options, {
                    'enum': {
                        url: options.enumURL,
                        debounce: options.enumDebounce,
                        limit: options.enumLimit,
                        cache: options.enumCache
                    },
                    dataAdapter: EnumAdapter
                });
            }

            $.extend(select2Options, {
                creatorURL: options.createURL,
                templateResult: renderSelect2Result,
                resultsAdapter: resultsAdapter
            });
        }, undefined, true);

        if (options.allowClear && Object.isEmpty(element.find('option[value=""]'))) {
            element.append($('<option value="">${placeholder}</option>'.template({placeholder: placeholder})));
        }

        /*
         * Select2 Issue !
         * Generate a 'data-select2-id' here or the element 'id' will be used EVEN if multiple ones
         * are on the same page, for instance when you open a popup...
         */
        element.attr('data-select2-id', _.uniqueId('select2-'));

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
        /*
         * If the "EnumAdapter" is enabled, we cannot refresh the data from the
         * existing options because they are synced only when a item is selected
         * and this cause a rendering conflict : we have the 'placeholder' twice and thats all...
         * TODO : find a way to do it swiftly
         */
        if (Object.isEmpty(this.options().enumURL) === false) {
            return this;
        }

        // var data = creme.model.ChoiceGroupRenderer.parse(this.element);

        /*
         * The "DataAdapter" is a bit stupid : <optgroup> are duplicated because they don't have any id...
         * So we have to remove them
         */
        /*
        this.element.find('optgroup').remove();
        this.element.select2({
            data: convertToSelect2Data(data)
        });
        */

        /*
         * Calling $(element).select2({data: ...}) it will create a NEW instance
         * with default options even if Select2 is already active... Not really what we want.
         * But the 'change' event seems to do the magic itself in this case.
        */
        this.element.trigger('change');

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
