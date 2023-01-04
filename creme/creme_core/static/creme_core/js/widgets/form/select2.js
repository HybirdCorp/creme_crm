/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2022-2023 Hybird
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
                return ngettext('Please enter %d or more character', 'Please enter %d or more characters', remainingChars).format(remainingChars);
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

function normalizeSelect2Item(item) {
    if (Array.isArray(item)) {
        return {
            id: item[0],
            text: item[1],
            disabled: false,
            selected: false
        };
    } else {
        var output = {
            id: item.value || item.id,
            text: item.label || item.text,
            disabled: item.disabled || false,
            selected: item.selected || false
        };

        if (item.group) {
            output['group'] = item.group;
        }

        return output;
    }
};

function convertToSelect2Data(data) {
    data = data || [];

    var optgroups = {};
    var options = [];

    data.filter(function(item) {
        return item.visible !== false;
    }).forEach(function(item) {
        var option = normalizeSelect2Item(item);

        if (option.group) {
            var optgroup = optgroups[option.group] = (optgroups[option.group] || {
                text: option.group,
                children: []
            });

            optgroup.children.push(option);
        } else {
            options.push(option);
        }
    });

    if (!_.isEmpty(optgroups)) {
        options = options.concat(_.values(optgroups));
    }

    return options;
}

/*
function mergeSelect2Data(initial, items) {
    var output = [];
    var groups = {};

    initial.forEach(function (item) {
        if (item.children) {
            groups[item.text] = item;
        }

        output.push(item);
    });

    items.forEach(function(item) {
        if (item.children) {
            var group = groups[item.text];

            if (group) {
                group.children = group.children.concat(item.children);
            } else {
                output.push(item);
            }
        } else {
            output.push(item);
        }
    });

    return output;
}
*/

function renderSelect2Result(state) {
    if (state.pinned) {
        return $(
           '<span class="select2-results__pin">${text}</span>'.template(state)
        );
    } else {
        return state.text;
    }
}

function selectionRenderer(options) {
    function renderer(state, container) {
        if (options.selectionShowGroup) {
            var group = $(state.element).parent('optgroup').get();
            return group.length ? group[0].label + ' − ' + state.text : state.text;
        } else {
            return state.text;
        }
    }

    renderer.options = options;
    return renderer;
}

function clearSelect2Data(items) {
    S2.require(['select2/utils'], function(Utils) {
        items.each(function() {
            Utils.RemoveData(this);
        });
    }, undefined, true);
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
            /*
             * Trigger a new query if we get an event from the "more" button
             */
            params = $.extend({}, this._lastEnumParams);
            params.limit += this.enumOptions.limit;
            this.trigger('query', params);
        }.bind(this));

        container.on('enum:add', function(params) {
            /*
             * Reset cache if items have been added with the "create" button
             *
             * TODO : This will remove the ENTIRE cache, so it should be a good
             * idea to improve this part.
             */
            if (this._queryBackend instanceof creme.ajax.CacheBackend) {
                this._queryBackend.reset();
            }
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
                self.addItems(convertToSelect2Data(items || []), container);
            });

            self.trigger('close');
            form.open();
        });

        function extractTerms(items) {
            var terms = [];

            items.forEach(function(item) {
                if (item.children) {
                    terms.push.apply(terms, extractTerms(item.children));
                } else {
                    terms.push(item.text);
                }
            });

            return terms;
        }

        container.on('results:all', function(params) {
            var term = params.query.term;
            var texts = extractTerms(params.data.results);

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
/*
    CreatorButton.prototype.addItems = function(decorated, items, container) {
        var dataAdapter = this._dataAdapter;
        var initial = this.$element.children().map(function() {
            return dataAdapter.item($(this));
        }).get();

        container.trigger('results:all', {
            query: {
                term: ''
            },
            data: {
                results: mergeSelect2Data(initial, items)
            }
        });
    };
*/
    CreatorButton.prototype.allItems = function(decorated) {
        var dataAdapter = this._dataAdapter;
        return this.$element.children().map(function () {
          return dataAdapter.item($(this));
        }).get();
    };

    CreatorButton.prototype.addItems = function(decorated, items, container) {
        var options = [];
        var dataAdapter = this._dataAdapter;
        var existingItems = this.allItems();

        // Select first item or the first group item
        if (items.length) {
            if (items[0].children) {
                items[0].children[0].selected = true;
            } else {
                items[0].selected = true;
            }
        }

        // Populate <select> and Select2 storage with the new items
        items.forEach(function(item) {
            var $option;

            if (item.children) {
                var existingGroup = existingItems.find(function(existing) {
                    return existing.children && item.text === existing.text;
                });

                if (existingGroup) {
                    /* Merge group item data with existing */
                    item = $.extend(true, {}, existingGroup, item, {
                        children: existingGroup.children.concat(item.children)
                    });

                    /* Create a NEW option with a NEW storage (the exising one cannot be updated -_-) */
                    $option = dataAdapter.option(item);

                    /* Replace <optgroup> element within the DOM.
                     * We have to do it to make the internal ids match between the DOM and the dropdown
                     */
                    $(existingGroup.element).replaceWith($option);
                } else {
                    $option = dataAdapter.option(item);
                }

                $option.append(
                    item.children.map(function(item) {
                        return dataAdapter.option(item);
                    })
                );
            } else {
                var existingItem = existingItems.find(function(existing) {
                    return item.id === existing.id;
                });

                if (existingItem) {
                    $option = dataAdapter.option($.extend(true, {}, existingItem, item));
                    $(existingItem.element).replaceWith();
                } else {
                    $option = dataAdapter.option(item);
                }
            }

            options.push($option);
        });

        // Add the new <option>/<optgroup> to the DataAdapter.
        dataAdapter.addOptions(options);

        // Trigger selection change
        this.$element.trigger('change.select2');

        // Sync the dropdown content with the new <select> options
        container.trigger('enum:add', {
            data: items
        });
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
            selectionShowGroup: element.data('selectionShowGroup'),
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
            templateSelection: selectionRenderer(options)
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

            /*
             * Prevents memory leak fixed in 4.1.0-rc0
             * (see https://github.com/select2/select2/pull/5965)
             */
            clearSelect2Data(this.element);

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
         *
         * But clearing the cache (options values/labels are now out of sync) and triggering
         * a 'change' event seems to do the magic in this case.
        */
        clearSelect2Data(this.element.find('option, optgroup'));
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
